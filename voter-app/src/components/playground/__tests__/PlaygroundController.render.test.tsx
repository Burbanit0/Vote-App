import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// PlaygroundProvider pulls in the live-diagnostics hook, which debounces a call
// to profileApi — mock it so the test doesn't hit the network and settles fast.
vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockResolvedValue({
    methods: { plurality: { winner: 'A' } },
    condorcet_winner: 'A',
    inter_method_agreement: 1,
    cycle_rate: 0.1,
    candidate_names: ['A', 'B'],
    display_points: [],
    candidate_points: null,
    num_voters: 300,
    ballot_type: 'rank_truncated',
    ballot_expressiveness: 0.4,
    ballot_cognitive_load: 0.3,
    sample_ballot: { A: 1, B: 0.5 },
    winner_flips: [],
    incompatible_methods: [],
  }),
}));

import {
  PlaygroundProvider,
  usePlaygroundCtx,
  useMethodSelection,
  type PlaygroundCtx,
} from '../PlaygroundController';

// What this test proves, and what it deliberately doesn't:
//
// The context VALUE object returned by useController() is now memoized, so an
// ancestor re-render that touches none of its ~70 dependencies (a parent
// passing a structurally-new `children` element, a StrictMode double-invoke,
// Fast Refresh) does not hand every usePlaygroundCtx() consumer a *new object
// reference* — this test asserts exactly that: object identity survives an
// unrelated ancestor re-render.
//
// It does NOT assert that consumer *render counts* drop, because they mostly
// don't: every direct usePlaygroundCtx() consumer (ElectorateMoment,
// InstrumentPanel, …) subscribes to ONE monolithic context via useContext, so
// React re-renders all of them whenever ANY of its ~67 fields legitimately
// changes — which is most interactions, since almost everything here derives
// from the same `config`/`playground` store slices. Memoizing the container
// object cannot fix that; only splitting into several smaller contexts would
// (the escape hatch this component's own review flagged, previously not
// attempted — a much larger, separate change touching every consumer).
//
// One slice HAS been split out since: `enabledRules`/`setEnabledRules`/
// `lensItems` moved to their own useMethodSelection() context (2026-09-13,
// flake-hunter investigation into a WebKit-only e2e timeout — see git log
// on this file). MethodMoment's checkbox toggles used to re-render every
// usePlaygroundCtx() consumer, including the SVG/D3-heavy LeaderCanvas via
// InstrumentPanel; under real CI-runner CPU contention, WebKit's per-frame
// cost for that re-render pattern was high enough to blow past Playwright's
// 30s actionability timeout on a 28-checkbox uncheck loop (Chromium/Firefox
// unaffected by the identical contention). Toggling a rule now only
// re-renders MethodMoment, ValuesLabPanel and BilanMoment — the three real
// consumers of that slice — asserted directly in the second test below.
let captured: PlaygroundCtx[] = [];

function Capture() {
  const ctx = usePlaygroundCtx();
  captured.push(ctx);
  return null;
}

function Harness() {
  const [, bump] = React.useReducer((c: number) => c + 1, 0);
  return (
    <div>
      <button onClick={() => bump()}>bump</button>
      <PlaygroundProvider>
        <Capture />
      </PlaygroundProvider>
    </div>
  );
}

describe('PlaygroundController context memoization', () => {
  it('keeps the same context object reference across an unrelated ancestor re-render', async () => {
    captured = [];
    render(<Harness />);

    // Let the debounced live-diagnostics call (350ms) resolve so its setState
    // calls settle before the assertion window below.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });
    await waitFor(() => expect(captured.length).toBeGreaterThan(0));

    const settled = captured[captured.length - 1];

    // Re-render the ancestor for a reason that touches no playground state at all.
    fireEvent.click(screen.getByText('bump'));
    await act(async () => {
      await Promise.resolve();
    });

    const afterBump = captured[captured.length - 1];
    expect(afterBump).toBe(settled);
  });

  it('toggling a method-selection field does not re-render plain usePlaygroundCtx() consumers', async () => {
    let mainRenders = 0;
    let lastEnabledCount: number | null = null;

    function MainOnlyConsumer() {
      usePlaygroundCtx();
      mainRenders++;
      return null;
    }

    function Toggler() {
      const { enabledRules, setEnabledRules } = useMethodSelection();
      lastEnabledCount = enabledRules.size;
      return (
        <button
          onClick={() =>
            setEnabledRules((prev) => {
              const next = new Set(prev);
              const [first] = next;
              if (next.size > 1 && first !== undefined) next.delete(first);
              return next;
            })
          }
        >
          toggle
        </button>
      );
    }

    render(
      <PlaygroundProvider>
        <MainOnlyConsumer />
        <Toggler />
      </PlaygroundProvider>
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });
    await waitFor(() => expect(mainRenders).toBeGreaterThan(0));

    const rendersBeforeToggle = mainRenders;
    const countBeforeToggle = lastEnabledCount;

    fireEvent.click(screen.getByText('toggle'));
    await act(async () => {
      await Promise.resolve();
    });

    // The method-selection slice really did change...
    expect(lastEnabledCount).toBe((countBeforeToggle ?? 0) - 1);
    // ...but a component that only reads usePlaygroundCtx() was not re-rendered
    // by that change — the whole point of splitting this slice into its own
    // context (see the comment above this describe block).
    expect(mainRenders).toBe(rendersBeforeToggle);
  });
});
