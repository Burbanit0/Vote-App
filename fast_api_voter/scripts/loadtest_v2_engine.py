"""fast_api_voter/scripts/loadtest_v2_engine.py — Locust load test for the
/api/v2 simulation surface (Lot 8.2, PLAN_SOLIDITE_TECHNIQUE.md: "Le
rate-limit 120/min a été calibré au jugé ; un test de charge donne le vrai
plafond du pool de threads" -- the 120/min rate limit was calibrated by feel;
a load test gives the real ceiling of the thread pool it was guessed
against).

**A live finding this file's own first draft got wrong, kept here on
purpose.** The first version of this experiment used a near-zero wait_time
on every user class. Result: 45% of requests failed -- ALL 429s, zero
503s/timeouts. That's not the thread-pool ceiling, it's the much lower,
much-easier-to-hit per-path rate limit (120/min = 2 req/s): closed-loop
traffic with no pacing crosses 2 req/s on a single path almost instantly,
long before 4 concurrent CPU-bound workers ever queue. That IS a real
finding -- for a single endpoint under realistic traffic, the rate limiter
is the ceiling a user hits first, not the thread pool -- but it isn't the
thread-pool ceiling this item is actually asking about, and it would have
masked it if left as the only result. See
docs/exploration/EXP-007-locust-v2-thread-pool-ceiling.md for both findings
with real numbers.

To isolate the thread-pool ceiling specifically, `MonteCarloUser` below
relies on a property confirmed by reading worker_dispatch.py's actual
ordering rather than assuming it: `check_v2_rate_limit` (the rate limiter)
runs as a FastAPI dependency BEFORE the route handler body, which is what
calls `run_worker_bounded` (the semaphore). A closed-loop Locust user can't
send its NEXT request until the current one's full round trip (rate-limit
check + semaphore queueing + compute) completes. Monte Carlo's own
multi-second service time therefore self-throttles each simulated user's
REQUEST rate to comfortably under 120/min even at zero wait_time, while
still piling up more in-flight requests than the semaphore's 4 slots once
enough users run concurrently -- letting `-u` ramp concurrency without ever
tripping that path's own rate limit, isolating the semaphore's queuing
behaviour from the rate limiter's.

**Manual/local tool, NOT a CI gate.** Same treatment as EXP-003's runtime
coverage script (docs/exploration/EXP-003-couverture-runtime-e2e.md): load
tests are inherently expensive, slow, and machine-dependent -- a meaningful
ceiling on this dev machine is not the same number on a shared GitHub
Actions runner, and running this on every PR would be pure noise (or need
re-calibrating on every runner class change). This is a tool to run by hand
when investigating capacity, documented here and in the EXP writeup, not
wired into any workflow.

**What "the real ceiling" turned out to mean here.** Reading api/core/
worker_dispatch.py before writing a single request: every /api/v2 route
(profile-simulate, monte-carlo, ...) is `async def`, but hands its CPU-bound
compute to `asyncio.to_thread` through a SHARED `asyncio.Semaphore(4)` --
`MAX_CONCURRENT_WORKERS = 4` -- not the raw default executor's
`min(32, cpu_count + 4)`. That semaphore is process-global: a Monte Carlo
run and a profile-simulate call compete for the SAME 4 slots. The rate
limiter (api/core/ratelimit.py, `check_v2_rate_limit`, 120/minute) is, by
contrast, PER PATH (slowapi's `key_style="url"`) -- every route gets its
own independent bucket, and (`get_remote_address`) also per client IP.

**Two user classes, calibrated from real measurements taken before writing
this file** (see EXP-007 for the direct, no-HTTP timings against the worker
functions):

- `ProfileSimulateUser` -- the actual endpoint 120/min was calibrated
  against (ratelimit.py's own docstring: a debounced live call fired on
  every Playground config change). ~13ms at the default config, ~125ms at
  the production ceiling (1000 voters / 8 candidates). An explicit
  `wait_time` keeps it around ~1 req/s -- comfortably under its own
  120/min budget -- standing in for realistic background UI traffic that
  coexists with the heavier class below, not for finding its own ceiling
  (closed-loop pressure on this endpoint alone just finds the rate limiter,
  per the note above).
- `MonteCarloUser` -- default config (num_runs=100, num_voters=150),
  ~1-4s/call depending on machine contention (both measured directly). This
  is the one that matters for this experiment: `wait_time = 0`, and its own
  long service time is what self-throttles its request rate (see above) --
  ramp `-u` across runs and watch its p95/p99 latency and error mix for
  where 4-concurrent-worker queueing starts, and whether it's 503s (the
  semaphore's 180s timeout, api/core/worker_dispatch.py) or 429s (the rate
  limiter) that eventually shows up first at high `-u`.

Usage (manual, from fast_api_voter/ -- pick a port your own server is
actually listening on; localhost can already have something else bound to
a common port, confirm with a plain curl before trusting results against
it):

    uvicorn api.main:app --port 4436 &
    curl -X POST http://localhost:4436/api/v2/simulations/monte-carlo -d '{}'  # sanity check
    locust -f scripts/loadtest_v2_engine.py --headless \\
        -u 16 -r 4 -t 30s --host http://localhost:4436 --csv=/tmp/loadtest

`-u` = concurrent simulated users, `-r` = spawn rate/s, `-t` = duration.
Ramp `-u` across runs (e.g. 2, 8, 16, 32) and watch `--csv`'s
`*_stats.csv` p95/p99 columns -- the point where they stop being flat and
start growing roughly linearly with `-u / 4` is the real thread-pool
ceiling, not a guess. See the EXP writeup for the numbers actually observed
here.
"""
from __future__ import annotations

from locust import HttpUser, task, between, constant

_PROFILE_PAYLOAD_DEFAULT = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob", "x": 0.5, "y": 0.2},
        {"name": "Carol", "x": 0.0, "y": 0.3},
    ],
    "num_voters": 300,
}

_MONTE_CARLO_PAYLOAD_DEFAULT = {
    "num_runs": 100,
    "num_voters": 150,
}


class ProfileSimulateUser(HttpUser):
    """Realistic background Playground traffic -- paced well under its own
    120/min budget on purpose (see module docstring: this class exists to
    coexist with MonteCarloUser, not to find its own ceiling)."""

    weight = 1
    # ~13ms service time is too fast to be self-limiting the way Monte
    # Carlo's is (see module docstring) -- an explicit wait_time is the only
    # way to keep this class's own request rate under its 120/min bucket
    # regardless of how many instances Locust spawns.
    wait_time = constant(1.0)

    @task
    def profile_simulate_default(self) -> None:
        self.client.post(
            "/api/v2/election/profile-simulate",
            json=_PROFILE_PAYLOAD_DEFAULT,
            name="/profile-simulate (default 300v/3c)",
        )


class MonteCarloUser(HttpUser):
    """The heavy CPU-bound endpoint used to find the shared worker_dispatch
    semaphore's real ceiling -- see module docstring for why zero wait_time
    here is deliberate and still stays under this path's own rate limit."""

    weight = 4
    wait_time = between(0.0, 0.0)

    @task
    def monte_carlo_default(self) -> None:
        self.client.post(
            "/api/v2/simulations/monte-carlo",
            json=_MONTE_CARLO_PAYLOAD_DEFAULT,
            name="/monte-carlo (default 100runs/150v)",
        )
