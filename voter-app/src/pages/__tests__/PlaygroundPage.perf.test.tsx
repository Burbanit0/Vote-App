import React, { Profiler, type ProfilerOnRenderCallback } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Lot 8 — "Invariant de perf du form-lock" (PLAN_SOLIDITE_TECHNIQUE.md). The
// voter-ui skill documents the form-lock invariant ("at first paint, only the
// *-toggles are in the DOM, no heavy panel is mounted") and PlaygroundPage.test.tsx
// already enforces its SHAPE (specific testids absent from the DOM). This file
// adds the missing half: an actual React Profiler MEASUREMENT, with real
// assertions on what the shape test cannot see — render count and render cost.
//
// Two assertion styles were tried and only one survived contact with real
// numbers (see EXP-004 in docs/exploration/ for the full experiment log):
//
// - An ABSOLUTE millisecond ceiling on first paint was rejected outright: the
//   very first render in a fresh Vitest worker is inflated ~3-5x by JIT/module
//   warm-up alone (58ms cold vs ~13ms warm for the IDENTICAL code, measured
//   over 8 consecutive runs) — that swamps any real regression small enough to
//   matter. This project has already been burned by exactly this category of
//   mistake once (CI timeout tuning, see PLAN_SOLIDITE_TECHNIQUE.md Lot 3 "Timeouts
//   & backpressure"), so it is not repeated here.
// - A RENDER-COUNT invariant (how many discrete commits happen synchronously
//   before the page settles, with no user interaction) turned out to be
//   deterministic — stable at exactly 2 across 8+ runs — and it does catch a
//   real regression class: staged/chained eager effects that aren't gated
//   behind any user action (verified by deliberately injecting one — see
//   EXP-004). It does NOT catch an eager DOM mount (that's what the existing
//   shape test in PlaygroundPage.test.tsx is for) or heavy work stuffed inside
//   a single effect body (React's Profiler only times the render/commit phase,
//   never the body of an effect callback — also verified empirically).
// - A RELATIVE duration comparison — a real, awaited compute-heavy interaction
//   (opening the probability lens, which drives an actual client-side
//   simulation) against a trivial disclosure-panel toggle, both measured in the
//   SAME test run on the SAME machine — is what actually has teeth: the heavy
//   path costs 5x-12x the cheap one across 6 independent measurements, so a 3x
//   floor leaves comfortable headroom under CI variance while still being far
//   above noise. This is the concrete evidence that gating real computation
//   behind explicit interaction (rather than paying it at first paint) is a
//   real, measurable win, not just a documented intention.

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));
vi.mock('../../services/assemblyApi', () => ({
  runAssemblyScorecard: vi.fn().mockResolvedValue({ replications: 0, structures: {} }),
  runAssembly: vi.fn().mockResolvedValue(null),
}));
vi.mock('../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockResolvedValue({
    methods: { plurality: { winner: 'A' } },
    condorcet_winner: 'A',
    inter_method_agreement: 1,
    cycle_rate: 0.12,
    candidate_names: ['A', 'B'],
    display_points: [],
    candidate_points: null,
    num_voters: 300,
    ballot_type: 'rank_truncated',
    ballot_expressiveness: 0.4,
    ballot_cognitive_load: 0.3,
    sample_ballot: { A: 1, B: 0.5, C: 0 },
    winner_flips: [],
    incompatible_methods: [],
  }),
}));

import { MemoryRouter, Routes, Route } from 'react-router';
import PlaygroundPage from '../PlaygroundPage';
import {
  useElectionStore,
  DEFAULT_PLAYGROUND,
  DEFAULT_CONFIG,
} from '../../stores/useElectionStore';

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    playground: { ...DEFAULT_PLAYGROUND },
    config: { ...DEFAULT_CONFIG },
  });
});

/** One React commit's cost, as reported by <Profiler onRender>. */
interface Commit {
  actualDuration: number;
}

function renderProfiled(commits: Commit[]) {
  const onRender: ProfilerOnRenderCallback = (_id, _phase, actualDuration) => {
    commits.push({ actualDuration });
  };
  return render(
    <MemoryRouter initialEntries={['/playground']}>
      <Routes>
        <Route
          path="/playground"
          element={
            <Profiler id="playground" onRender={onRender}>
              <PlaygroundPage />
            </Profiler>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('PlaygroundPage form-lock — React Profiler invariant', () => {
  it('first paint settles in a small, bounded number of synchronous commits', () => {
    const commits: Commit[] = [];
    renderProfiled(commits);

    // Today this is exactly 2: the initial mount, plus one immediate commit
    // from useProfileDiagnostics flipping its `loading` flag true (a real,
    // legitimate state transition — not the Duverger/Recharts/heavy-panel
    // class of work the form-lock invariant is actually guarding against).
    // A THIRD (or more) commit here means something new fires synchronously
    // at mount without any user interaction — worth a second look before
    // bumping this number. See the file header for what this can and can't
    // detect.
    expect(commits.length).toBeLessThanOrEqual(2);
    expect(screen.getByTestId('playground-page')).toBeInTheDocument();
  });

  it('gated compute (probability lens) costs measurably more than a trivial disclosure toggle', async () => {
    // Cheap side: opening a disclosure panel that renders a form, no
    // simulation attached (Électorat moment, default lens closed).
    const cheapCommits: Commit[] = [];
    const cheap = renderProfiled(cheapCommits);
    cheapCommits.length = 0; // isolate the click from the mount commits above
    fireEvent.click(cheap.getByTestId('module-electorate-toggle'));
    const cheapCost = cheapCommits.reduce((sum, c) => sum + c.actualDuration, 0);
    cheap.unmount();

    // Heavy side: switching the central lens to 'probability', which drives a
    // real client-side simulation (LeaderCanvas's lottery bars) — this is
    // exactly the kind of work the form-lock invariant keeps OUT of first
    // paint. Waited for real, like PlaygroundPage.test.tsx's own lens test.
    const heavyCommits: Commit[] = [];
    const heavy = renderProfiled(heavyCommits);
    fireEvent.click(heavy.getByTestId('moment-method'));
    heavyCommits.length = 0;
    fireEvent.click(heavy.getByTestId('lens-probability'));
    await waitFor(() => expect(heavy.getByTestId('problens')).toBeInTheDocument(), {
      timeout: 5000,
    });
    const heavyCost = heavyCommits.reduce((sum, c) => sum + c.actualDuration, 0);
    heavy.unmount();

    // Observed over 6 independent runs while designing this test: 5.4x-11.7x.
    // 3x is a deliberately conservative floor, not the measured baseline —
    // see EXP-004 for why an absolute ms figure isn't used here instead.
    expect(heavyCost).toBeGreaterThan(cheapCost * 3);
    // The heavy path also always takes more distinct commits (loading → data)
    // than the single synchronous toggle commit — a second, count-based signal
    // that doesn't depend on timing at all.
    expect(heavyCommits.length).toBeGreaterThan(cheapCommits.length);
  });
});
