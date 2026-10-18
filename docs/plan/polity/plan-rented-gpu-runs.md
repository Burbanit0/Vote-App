# Rented-GPU runs: runbook and the first Qwen3.8-27B probes

> **status:** live — first findings, 2026-10-17; the architecture for a full rented-GPU test is prepared (§10), not yet run. (Set 2026-10-17; `docs/README.md` lists every plan.)

This is the first record of running polity against a rented GPU with a model larger than the
shipped Qwen3-8B. It has two jobs: to let the next person repeat the setup in minutes, and to say
what the three runs below show, and what they do not. It is a starting point for the architecture
of a full test, not that architecture.

Everything here comes from one session (2026-10-17) on one pod. Numbers are reproduced from the
run files named in §9; where a number is an estimate or was read from a partial source, it says so.

---

## 1. Summary

- **A tunnelled rented server works end to end.** vLLM 0.31.0 on one RTX PRO 6000 Blackwell (96 GB),
  reached through an SSH tunnel, ran the bake-off, a 2-year and an 8-year polity run with no crash.
  This meets the Phase 0 exit in `plan-polity-agency-roadmap.md` ("one tunnelled rented smoke run
  completes"; chamber unit fallback below 1% on a 2-year p200 run: 0 of 270).
- **Qwen3.8-27B (FP8) is reliable on the decisions it was given.** 8-year p100 run: 0 fallbacks,
  0 retries, 0 errors on 1,171 decision calls.
- **It differs from the recorded 8B behaviour on two bake-off families:** `coalition_decision`
  responds to its cost (flat on the 8B, Granite and Gemma), and candidacy is far more selective and
  more consistent with the threshold rule. `vote_cast` and `pressure_action` are fully valid.
  `campaign_positioning` is the worst case (7 of 10 valid, 184 s per request).
- **It is slow.** Leader turns, chamber deliberation and forum posts take 39–55 s per call because
  each uses the full 2,047-token thinking budget. I estimate roughly an order of magnitude slower
  than the 8B with EAGLE-3 (see §6: not measured on the same config).
- **The GPU was mostly idle.** In the part of the vLLM log I could read: at most 15 concurrent
  requests, 11.4% KV cache, about 550 tokens/s peak. The run's serial phases are the limit, not the
  card and not `--workers`.
- **There is no like-for-like 8B run yet.** Every "difference" with the 8B below is against the
  8B's behaviour as recorded elsewhere, not a paired comparison. That is the first thing to fix (§7).
- **The shipped tooling assumes a local server.** `launch_full_run.sh` and `run_provenance` expect a
  local docker container and `nvidia-smi`; a remote full run needs its own launch and telemetry
  (§7, G1–G3).

## 2. What was run

| # | Run | Config | Result |
|---|---|---|---|
| 1 | Bake-off, `rtxpro6000-qwen38-27b` | `scripts/run_bakeoff.py --model qwen3.8:27b`; case bank `709265958412f811`, 174 cases | 225 calls; thinking and logprob gates pass; re-run noise floor 100% |
| 2 | Probe `probe-2y-p200-qwen38-27b-seed42` | 2 years, 200 citizens, 30 seats, seed 42, `--profile exploration`, 12 workers, relaxed | 2,394 s, 8 ticks, 1,138 decisions, 0 fallbacks, 5 retries |
| 3 | Probe `probe-8y-p100-qwen38-27b-w24-seed42` | 8 years, 100 citizens, 15 seats, seed 42, `--profile exploration`, 24 workers, relaxed | 6,118 s (102 min), 32 ticks, 1,893 decisions, 0 fallbacks, 0 retries |

Both probes ran the code at `origin/polity` `e11971af` (PR #960), from a detached worktree, with
`POLITY_LOG_PROMPTS=1`. The model was served as `qwen3.8:27b` (profile `QWEN3_8_27B_FP8_VLLM` in
`api/domain/polity/model_profiles.py`, `measured=False`: it inherits the 8B's chunk sizes and
thinking budgets).

## 3. Runbook

### 3.1 Pick the hardware

Live Runpod catalogue on 2026-10-17, Secure Cloud, per GPU-hour. Stock moves; read it again.

| GPU | VRAM | $/h | Note |
|---|---|---|---|
| RTX PRO 6000 Blackwell | 96 GB | 2.49 | Best VRAM per dollar; Blackwell, so NVFP4 loads. PCIe-class: no NVLink for tensor parallelism. **Used here.** |
| H200 SXM | 141 GB | 5.29 | Room for ~70B FP8 on one card |
| H100 SXM | 80 GB | 3.99 | The card `docker-compose.llm-h100.yml` was written for |
| A100 SXM | 80 GB | 1.79 | No FP8/NVFP4 hardware path |
| B200 / B300 | 180 / 288 GB | 7.99 / 8.99 | Out of stock or Low in the multi-GPU reads |

What fits one 96 GB card at `--gpu-memory-utilization 0.90`: about 60–65 GB of weights once ~20–25 GB
is kept for KV cache with many workers. That is roughly 30B in BF16, 60B in FP8, ~110B in NVFP4/W4A16
(estimates, not measurements; count total parameters for a MoE).

The RTX PRO 6000 showed Low stock in every data centre, and a create in EUR-IS-2 still succeeded
first try.

### 3.2 Pod

Created with the Runpod MCP `create-pod` (values; no secrets):

```json
{
  "name": "polity-qwen38-27b",
  "cloud": "SECURE",
  "image": "vllm/vllm-openai:v0.31.0",
  "gpu": { "id": "NVIDIA RTX PRO 6000 Blackwell Server Edition", "count": 1, "minCudaVersion": "13.0" },
  "dataCenterIds": ["EU-RO-1", "EUR-IS-1", "EUR-IS-2"],
  "disk": 40,
  "mounts": { "persistent": { "size": 100, "path": "/workspace" } },
  "ports": ["22/tcp"],
  "startSsh": true,
  "env": { "HF_HOME": "/workspace/hf" },
  "entrypoint": ["/bin/bash", "-c"],
  "cmd": ["<the start command below>"]
}
```

`startSsh` injects `PUBLIC_KEY` (your account's registered keys; register the **public** half only).
Port 8000 is deliberately not exposed.

The `vllm-openai` image has no sshd, so the start command installs one, applies the lock-down, then
`exec`s vLLM. The container disk is wiped on every restart, so the lock-down must be in the command,
not applied by hand afterwards:

```bash
apt-get update -qq && apt-get install -y -qq openssh-server >/dev/null \
&& mkdir -p /root/.ssh /run/sshd /etc/ssh/sshd_config.d \
&& echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys \
&& chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys \
&& printf 'PasswordAuthentication no\nPermitRootLogin prohibit-password\nAllowUsers root@<YOUR_PUBLIC_IP>\n' \
     > /etc/ssh/sshd_config.d/10-lock.conf \
&& ssh-keygen -A >/dev/null && sshd -t && /usr/sbin/sshd \
&& exec vllm serve --model Qwen/Qwen3.8-27B-FP8 \
     --revision 017b9c7af6b5689d5dd426a76e0bc077eb5ca20a \
     --served-model-name qwen3.8:27b --reasoning-parser qwen3 \
     --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' \
     --max-model-len 32768 --gpu-memory-utilization 0.90 \
     --host 127.0.0.1 --port 8000 --seed 42 --enable-prompt-tokens-details
```

The vLLM flags are those of `docker-compose.llm-h100.yml`, plus `--host 127.0.0.1`. `<YOUR_PUBLIC_IP>`
is the address sshd sees you connect from: connect once and read `$SSH_CLIENT` on the pod. The
revision pin is the `sha` of the HF repo recorded in that compose file.

Timings seen: image already cached on the host; checkpoint 28.75 GiB, downloaded in 41 s; model
load 54 s; `/health` answered within about 6 minutes of the first pod start (derived from log
timestamps and when polling began, not timed exactly). After a restart, with the weights already on
the persistent disk, 4 min 38 s to "Application startup complete" (the apt install included).

### 3.3 Tunnel and runs

```bash
# the pod's SSH address changes on every restart: read it from get-pod (ssh.direct), never reuse it
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N \
    -L 8100:localhost:8000 root@<pod-ip> -p <pod-ssh-port> -i ~/.ssh/<key>

curl http://localhost:8100/health                      # 200 when ready
python scripts/run_bakeoff.py --label <label> --model qwen3.8:27b --base-url http://localhost:8100/v1
python scripts/run_polity_flagship.py --engine llm --years 8 --population 100 --seats 15 --seed 42 \
    --profile exploration --workers 24 --reproducibility relaxed --max-batch-replays 2 \
    --base-url http://localhost:8100/v1 --model qwen3.8:27b --run-id <id> --output-dir <dir>
```

Run from a clean `origin/polity` worktree (`git worktree add --detach <dir> origin/polity`), with
`POLITY_LOG_PROMPTS=1`, and detach the run from the terminal
(`setsid nohup bash -c '...; echo EXIT $? >> <log>'`): a reboot or a closed session otherwise kills
it, and `--resume` is the only recovery.

### 3.4 Things that went wrong, and why

| Symptom | Cause | Fix |
|---|---|---|
| Tunnel: "Address already in use" on 8000 | A local vLLM already owns :8000 | Tunnel to another local port (8100 here) and pass `--base-url`. Do not stop the local server. |
| SSH times out after a pod restart | The public SSH port changes on restart (same IP) | Read `ssh.direct` from `get-pod` each time |
| "Host key verification failed" after a restart | Host keys are regenerated (ephemeral container disk); the new port is not in `known_hosts` | `-o StrictHostKeyChecking=accept-new`, once, for a pod you just created |
| Lock-down gone after a restart | It was applied by hand | It is in the start command (§3.2) |
| `--model` deprecation warning | vLLM 0.31.0 prefers a positional model | Harmless today; switch to positional before it is removed |
| Locked out after your IP changed | `AllowUsers root@<ip>` pins one address | `update-pod` with a new command, then restart. Skip `AllowUsers` if your IP is not stable: key-only login already blocks everyone without the key. |
| "LLM warm-up call (think=True) failed … finish_reason='length'" | Seen in all three runs, non-fatal | Not investigated; the warm-up budget is probably too small for this model |

## 4. Results

### 4.1 Bake-off (Qwen3.8-27B-FP8, 174 cases, seed 42)

One session, so there are no paired comparisons; `bakeoff_report.py` used it as its own control, and
its acceptance rows read "no" wherever the 27B differs from the 8B's known behaviour. Those rows are
differences, not failures.

| Family | Validity | What it shows |
|---|---|---|
| `coalition_decision` | 25/25 | P(join) by cost 0→0.98, 0.25→0.80, 0.5→0.15, 0.75→0.005, 1→0.001; separation −0.98. **Not flat** (known flat on the 8B, Granite 4.2 8B and Gemma 4 12B). |
| `candidacy_considered` | 20/20 | 71 of 500 declare (the 8B's recorded value: 202); agrees with the threshold rule on 449 of 500 (89.8%; the 8B's: 318). The 8B values are in `scripts/bakeoff_request_arms_results.md`. |
| `vote_cast` | 14/14 | 40/40 first-choice accuracy |
| `pressure_action` | 24/24 | 23/24 accurate |
| `chamber_deliberation` | 10/10 | moves with the drift knob; 104 s per request, 4,520 reasoning tokens |
| `representative_response` | 41/45 (91.1%) | **Still flat under pressure** (spread 0.027); 4 answers broke the motif rules |
| `campaign_positioning` | 7/10 (70%) | 3 failures (2 `content: null`, 1 invalid JSON), 3 truncated; 184 s and ~8,150 reasoning tokens per request |

Gates: thinking passes (1,500 reasoning tokens with thinking on, 0 off); logprobs aligned 16/16
(separation +0.999); re-run noise floor 100% (84/84 units).

### 4.2 The 2-year probe (200 citizens)

2,394 s over 8 ticks; 1,138 decisions (2.1 s/decision, 299 s/tick); 1,133 calls logged. No election
fell in the window (one president, holder 92, ended by run end), so nothing here exercises
campaign positioning. Effective number of parties 4.86. Fallback count 0, retries 5. Of the
discontented citizens asked for a pressure action, 92–100% chose to do nothing (`inaction_rate`
by tick); 273 of 285 chosen acts were act 0 and 12 were act 3.

### 4.3 The 8-year probe (100 citizens)

6,118 s over 32 ticks; 1,893 decisions (3.2 s/decision, 191 s/tick). Fallbacks 0, retries 0.

- **Politics.** Two elections (years 4 and 8); the president changed each time (holders 21 → 32 →
  16; mandate strengths 0.76 and 0.86). Two parties founded; effective number of parties 5.3 at the
  first election and 5.1 at the last. No recalls, no petitions. `inaction_rate` (the share of
  discontented citizens asked for a pressure action who choose act 0) was 1.0, 0.78 and 1.0 in the
  last three ticks; 382 of 391 chosen acts were act 0, 6 act 3, 3 act 4.
- **Calls** (decision-kind only; 1,171 of the 1,938 logged, the rest being 765 `budget_probe` calls,
  which end on `length` by design, and 2 warm-ups):

| Decision type | Calls | p50 s | p95 s | Reasoning tokens p50 | Truncated |
|---|---|---|---|---|---|
| `forum_post` | 495 | 38.6 | 60.3 | 1,190 | 0 |
| `pressure_action` | 391 | 2.1 | 2.8 | 0 | 0 |
| `chamber_deliberation` | 99 (5 units each) | 51.9 | 55.8 | 2,047 | 0 |
| `amendment_vote` | 75 | 21.9 | 54.7 | 627 | 0 |
| `president_turn` | 33 | 49.7 | 50.7 | 2,047 | 0 |
| `coalition_turn` | 30 | 53.1 | 54.2 | 2,047 | 0 |
| `nominee_turn` | 18 | 55.3 | 56.4 | 2,047 | 0 |
| `vote_cast` | 15 | 22.8 | 31.7 | 840 | 0 |
| `candidacy_considered` | 12 | 13.7 | 14.0 | 0 | 0 |

  Every chamber, president, coalition and nominee call reaches 2,047 reasoning tokens (the 2,048
  budget) and still returns a valid answer: the budget is binding, which is the same signal as
  OBS-023 on the 8B.
- **Tokens.** 4.36 M prompt tokens (1.80 M, 41%, served from the prefix cache) and 1.18 M
  completion tokens; the mean is about 190 completion tokens/s over the whole run.

### 4.4 Server load

From the vLLM container log, **the last ~96 stats intervals only** (the log was fetched at the end;
the run's full telemetry was not captured, see G3): at most 15 requests running and 3 waiting,
GPU KV cache at most 11.4%, generation at most 550 tokens/s, 21 intervals with 10 or more requests
running averaging 452 tokens/s, prefix-cache hit rate 41.7%. No preemption or error lines. These
are a floor on the peak, not the peak of the whole run.

## 5. Reading the results

What the evidence supports:

- the setup (§3) works and is repeatable;
- on this config the 27B does not produce invalid decisions;
- on two bake-off families (`coalition_decision`, candidacy) it behaves differently from what is
  recorded for the 8B;
- the run is limited by its own serial structure, not by the GPU.

What it does not support:

- **"The 27B is better."** No 8B ran the same code and config. The bake-off's 8B reference values
  come from earlier sessions on earlier code and prompts; two runs of one seed on one model do not
  make a comparison.
- **The passivity of citizens** (inaction near 1.0, no recalls) is not attributed. It may be the
  model, the exploration profile, or a population this small.
- **The profile is unmeasured.** Chunk sizes and thinking budgets are the 8B's. The budget binding on
  every leader call suggests they are wrong for this model, in an unknown direction.
- **Single seed per config.** Seed-level variation is unmeasured (the OBS log shows seeds differ).

## 6. Estimates for a full run (not measurements)

A 30-year, 500-citizen, 75-seat run has 3.75× the ticks of the 8-year probe and 5× its population.
Leader turns are serial and scale with ticks; citizen-level calls scale with population but run in
parallel on a GPU that was mostly idle. That gives a wide range, **roughly 8 to 25 hours**, or about
$20–60 on this card at $2.49/h. One more probe at p500 for 8 years would narrow it. For scale, the
roadmap records about 2 hours for the same full run on the 8B with EAGLE-3 on a local 16 GB card.

Spend this session: the pod ran about 3.8 hours, roughly $9.60 plus its disk (not itemised).

## 7. Toward a full test: gaps and decisions

Gaps found (what the next architecture has to cover):

| # | Gap | Evidence |
|---|---|---|
| G1 | `launch_full_run.sh` assumes a local docker server and GPU (`docker logs -f vllm-polity`, `nvidia-smi`). Calling `run_polity_flagship.py` directly works but loses the sleep inhibitor, the disk watchdog and the helper units. | Read in `scripts/launch_full_run.sh`; not run for this session |
| G2 | The pod lifecycle (create, lock down, tunnel, tear down) was done by hand through MCP calls. Nothing records it, and the SSH address changes on restart. | §3.4 |
| G3 | No remote telemetry. The vLLM log was fetched once at the end and covers only its tail; the local launcher's GPU/progress sampling does not reach a remote pod. | §4.4 |
| G4 | The run executes on a laptop over a tunnel. Sleep, reboot or a dropped tunnel kills it. | `--resume` is the only recovery |
| G5 | The 27B profile is `measured=False`; the thinking budget binds on every leader call. | §4.3 |
| G6 | No like-for-like 8B baseline for the same config. | §5 |
| G7 | The pod is under-used: parallel seeds would be nearly free in wall time (KV cache at most 11.4%). | §4.4 |

Decisions that belong to the owner (none is made here):

- **O1.** Run the simulation on the pod (no tunnel, survives a closed laptop, needs the repo and a
  Python environment there) or keep it local over a tunnel?
- **O2.** Which size for the full test: this 27B, a larger dense model on 2 cards, or a MoE?
- **O3.** Tune the 27B's thinking budgets and chunk sizes first (promote the profile to measured), or
  run the full test as a bake-off like the 8B's first full run?
- **O4.** Seed ensemble on one pod (G7), and how many seeds?
- **O5.** A lifecycle script (create / lock / tunnel / telemetry / terminate) in `scripts/`, or keep
  using the Runpod MCP by hand?

Suggested order, if the owner agrees: G6 (the 8B baseline on this exact config, on the local GPU),
then a 3-seed 8-year ensemble on the 27B (G7), then a p500 8-year probe to size the full run.

## 8. Security notes

The repo is public. Nothing from this session's pod belongs in it: not its address or port, not
your public IP, not key fingerprints.

- Only the **public** key goes to Runpod. Use a dedicated ed25519 key with a passphrase, mode 600,
  outside the repo, loaded in `ssh-agent`.
- vLLM has no authentication and `VllmJsonClient` sends no auth header (roadmap §1.4), so it must
  never be reachable from outside: bind it to `127.0.0.1` and use the tunnel. No Hugging Face token
  was needed (the model is public).
- The pod's SSH port is public. Key-only login and `AllowUsers` are the defences; verify them with
  `sshd -T` on the pod and a refused password login after each restart.
- Terminate the pod when the runs end. Billing stops only then; a stopped pod still pays for its
  disk. Whether the persistent disk is deleted with the pod was not checked: assume it is, and copy
  results off first (they already live on the machine that ran the simulation).

## 9. Reproduce and files

Run output is gitignored. On the session's machine:

- `~/Documents/Dev/polity-runs/rtxpro6000/probe-2y-p200-qwen38-27b-seed42{,.log}` and
  `…/probe-8y-p100-qwen38-27b-w24-seed42{,.log}`: `metrics.json`, `run/<id>/digest.json`,
  `llm_calls.jsonl`, `llm_prompts.jsonl`, `progress.json`.
- `fast_api_voter/scripts/bakeoff_runs/{rtxpro6000-qwen38-27b,scorecard.md,scorecard.json}` in the
  main checkout.

The per-type table in §4.3 is computed from `llm_calls.jsonl` (`kind == "decision"`, grouped by
`decision_type`, `latency_ms`, `reasoning_tokens`, `finish_reason`); the headline figures are in
`metrics.json` (`_meta`) and `progress.json`. The explorer (`polity-run-explorer.md`) can serve the
run folder as a root.

## 10. Architecture for a full test (prepared, not run)

The rented pod runs everything: vLLM, the simulation and the telemetry, side by side on `127.0.0.1`. The laptop only
creates the pod, watches it, fetches the results and terminates it. Nothing in this section has run on a pod yet.

### 10.1 What covers which gap

| Gap | How |
|---|---|
| G1, G4 | The runs execute on the pod, detached from any terminal. A closed laptop, a dropped tunnel or a reboot here does not touch them. The pod's start command restarts the chain, and the chain resumes every unfinished seed from its checkpoint, so a pod restart costs only the ticks since the last checkpoint. |
| G2 | The pod's start command does the whole set-up: lock-down, repo checkout at a pinned commit, Python environment, telemetry, runs, vLLM. Creating and terminating the pod stay manual (Runpod MCP or console), each with its price stated first. |
| G3 | `telemetry.py` writes one JSON line a minute for the whole session, beside the runs, so it is fetched with them. Each line holds the GPU, vLLM's queue, KV-cache and token counters, and every seed's progress. |
| G7 | `SEEDS` runs several seeds in parallel against the one server. |
| G5, G6 | Not covered here: see §10.5. |

### 10.2 Files (`fast_api_voter/scripts/rented/`)

| File | Where it runs | What it does |
|---|---|---|
| `pod_start.sh` | pod, as the container's entry point | Sets up ssh: key only, optional `ALLOW_FROM`. Builds a Python 3.14 environment with `requirements.lock.txt` on the persistent disk (once per lock file). Starts `telemetry.py` and `chain.sh` detached, then `exec`s vLLM on `127.0.0.1:8000`. |
| `chain.sh` | pod, or this machine | Every seed of `SEEDS` in parallel, each retried with `--resume` until its digest says completed. Writes `CHAIN_DONE`. Also runs locally against a local server, for the baseline (§10.5). |
| `telemetry.py` | pod | The per-minute sample, written to `/workspace/runs/telemetry.jsonl`. |
| `fetch.sh` | this machine | `rsync` of `/workspace/runs/` back here. Repeatable, and run once more before terminating. |

### 10.3 Creating the pod

As in §3.2 (same image, GPU, disk and ports, `startSsh`), with these environment variables and this start command.
`POLITY_SHA` must be a pushed commit that contains `scripts/rented/`.

```json
"env": {
  "HF_HOME": "/workspace/hf",
  "POLITY_SHA": "<a pushed polity commit>",
  "MODEL_REPO": "Qwen/Qwen3.8-27B-FP8", "MODEL_REVISION": "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a",
  "SERVED_NAME": "qwen3.8:27b",
  "RUN_LABEL": "<label>", "SEEDS": "1 2 3", "YEARS": "30", "POPULATION": "500", "SEATS": "75", "WORKERS": "24",
  "ALLOW_FROM": "<your public IP, or leave out>"
}
```

```bash
apt-get update -qq && apt-get install -y -qq git openssh-server rsync >/dev/null \
&& { [ -d /workspace/Vote-App ] || git clone -q https://github.com/Burbanit0/Vote-App /workspace/Vote-App; } \
&& git -C /workspace/Vote-App fetch -q origin && git -C /workspace/Vote-App checkout -q --detach "$POLITY_SHA" \
&& exec bash /workspace/Vote-App/fast_api_voter/scripts/rented/pod_start.sh
```

Leaving `RUN_LABEL` out starts the server and telemetry only. That is useful for the tunnelled way of §3.3, which
still works unchanged.

### 10.4 A session

1. **Create** the pod (§10.3) and note the hourly price. Read its `ssh.direct` address.
2. **Wait.** `ssh … 'tail -3 /workspace/runs/<label>.chain.log'` shows `seed N attempt 1` once vLLM answers. The first
   start downloads the weights and builds the environment; §3.2 saw `/health` within about 6 minutes, and the
   environment adds a few more.
3. **Watch.** `ssh … 'tail -1 /workspace/runs/telemetry.jsonl'` gives the GPU, vLLM and every seed's tick.
   `seed<N>.log` beside it has each run's own output.
4. **Fetch** whenever wanted: `scripts/rented/fetch.sh <ip> <port> <key>`. It writes to
   `~/Documents/Dev/polity-runs/rented/` by default.
5. **Terminate.** Once `/workspace/runs/<label>/CHAIN_DONE` exists, fetch once more, then terminate the pod. A
   stopped pod still pays for its disk.

### 10.5 Run plan, cheapest first

| Step | Where | Settings | Why |
|---|---|---|---|
| 1. 8B baseline (G6) | the local GPU, `chain.sh` with `BASE_URL=http://localhost:8000/v1` | The 8-year probe's own config: seed 42, 8 years, 100 citizens, 15 seats, exploration, 24 workers, relaxed | The like-for-like comparison §5 lacks. Free. |
| 2. Sizing probe | pod | 8 years, 500 citizens, 75 seats, `SEEDS="1 2 3"` | Narrows §6's 8-25 h. Measures whether three parallel seeds cost wall time. |
| 3. Full test | pod | 30 years, 500 citizens, 75 seats, `SEEDS` as decided | The full run |

The owner's decisions (§7) as this preparation leaves them:
- **O1:** the simulation runs on the pod. The tunnelled way stays available.
- **O2:** the model is three environment variables. The default is the probed 27B.
- **O3:** open. No tuning probe for the 27B's thinking budgets is built.
- **O4:** `SEEDS`; three are suggested.
- **O5:** scripts for everything but creating and terminating the pod.

### 10.6 Tested so far, and not

**Tested on this machine:**
- **`chain.sh`, deterministic engine:**
  - two seeds ran in parallel and finished;
  - a second start skipped them;
  - a seed whose process was killed mid-run came back with `--resume` and completed.
- **`telemetry.py`:** one sample against the local vLLM 0.31.0 read the GPU and vLLM's counters.
- **`pod_start.sh`, in the real `vllm/vllm-openai:v0.31.0` image, without a GPU and with a stub in place of `vllm`:**
  - sshd came up key-only;
  - `uv` built Python 3.14 with the locked dependencies;
  - telemetry wrote samples;
  - the chain ran a deterministic seed to `CHAIN_DONE`;
  - `vllm serve` was called with the arguments above.

**Not tested:**
- on a real pod;
- with the real vLLM serving while the simulation runs beside it;
- the clone at `POLITY_SHA`, which needs this branch merged;
- the 30-minute wait for a first weight download;
- restarting a pod mid-run.

