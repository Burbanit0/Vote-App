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

import { PlaygroundProvider, usePlaygroundCtx, type PlaygroundCtx } from '../PlaygroundController';

// What this test proves, and what it deliberately doesn't:
//
// The context VALUE object returned by useController() is now memoized, so an
// ancestor re-render that touches none of its ~70 dependencies (a parent
// passing a structurally-new `children` element, a StrictMode double-invoke,
// Fast Refresh) does not hand every usePlaygroundCtx() consumer a *new object
// reference* — this test asserts exactly that: object identity survives an
// unrelated ancestor re-render.
//
// It does NOT assert that consumer *render counts* drop, because they don't:
// every direct usePlaygroundCtx() consumer (ElectorateMoment, MethodMoment,
// InstrumentPanel, …) subscribes to ONE monolithic context via useContext, so
// React re-renders all of them whenever ANY of its ~70 fields legitimately
// changes — which is most interactions, since almost everything here derives
// from the same `config`/`playground` store slices. Memoizing the container
// object cannot fix that; only splitting into several smaller contexts would
// (the escape hatch this component's own review flagged, deliberately not
// attempted here — a much larger, separate change touching every consumer).
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
});
