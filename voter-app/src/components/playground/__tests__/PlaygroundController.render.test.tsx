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
  useStoreCtx,
  useJourneyCtx,
  useInstrumentCtx,
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
// That first test does NOT assert that consumer *render counts* drop, because
// for a usePlaygroundCtx() consumer they don't: it subscribes to the composed
// view of every slice, so React re-renders it whenever ANY of the ~67 fields
// legitimately changes. Memoizing the container object cannot fix that; only
// splitting into several smaller contexts and having a consumer subscribe to
// just the one(s) it reads can — which is what the four concern-split contexts
// (useStoreCtx / useJourneyCtx / useInstrumentCtx / useScorecardCtx,
// PLAN_SURFACE_EXTERIEURE.md §2.J) now do, asserted in the last two tests.
// InstrumentPanel, StrategyMoment and BilanMoment stay on usePlaygroundCtx()
// deliberately: they genuinely read (nearly) every slice, so narrowing them
// would buy nothing.
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

  // The same isolation, extended to the four concern-split contexts
  // (PLAN_SURFACE_EXTERIEURE.md §2.J). The high-frequency case is the one that
  // matters: dragging on the map must not re-render consumers that never read
  // the live spatial data.
  it('a drag-driven instrument change does not re-render store-only or journey-only consumers', async () => {
    let storeRenders = 0;
    let journeyRenders = 0;
    let composedRenders = 0;
    let lastYouX: number | null = null;

    function StoreOnly() {
      useStoreCtx();
      storeRenders++;
      return null;
    }
    function JourneyOnly() {
      useJourneyCtx();
      journeyRenders++;
      return null;
    }
    function ComposedConsumer() {
      usePlaygroundCtx();
      composedRenders++;
      return null;
    }
    function YouDragger() {
      const { youPos, setYouPos } = useInstrumentCtx();
      lastYouX = youPos.x;
      return <button onClick={() => setYouPos((p) => ({ ...p, x: p.x + 0.1 }))}>drag-you</button>;
    }

    render(
      <PlaygroundProvider>
        <StoreOnly />
        <JourneyOnly />
        <ComposedConsumer />
        <YouDragger />
      </PlaygroundProvider>
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });
    await waitFor(() => expect(storeRenders).toBeGreaterThan(0));

    const storeBefore = storeRenders;
    const journeyBefore = journeyRenders;
    const composedBefore = composedRenders;
    const youXBefore = lastYouX;

    fireEvent.click(screen.getByText('drag-you'));
    await act(async () => {
      await Promise.resolve();
    });

    // The instrument slice really did change...
    expect(lastYouX).toBeCloseTo((youXBefore ?? 0) + 0.1);
    // ...the composed usePlaygroundCtx() view saw it (proves the change
    // genuinely propagated, not that nothing happened)...
    expect(composedRenders).toBeGreaterThan(composedBefore);
    // ...but consumers that don't read the live spatial data did not re-render.
    expect(storeRenders).toBe(storeBefore);
    expect(journeyRenders).toBe(journeyBefore);
  });

  it('a moment change does not re-render instrument-only consumers', async () => {
    let instrumentRenders = 0;
    let lastMoment: string | null = null;

    function InstrumentOnly() {
      useInstrumentCtx();
      instrumentRenders++;
      return null;
    }
    function MomentSwitcher() {
      const { activeMoment, setActiveMoment } = useJourneyCtx();
      lastMoment = activeMoment;
      return <button onClick={() => setActiveMoment('method')}>go-method</button>;
    }

    render(
      <PlaygroundProvider>
        <InstrumentOnly />
        <MomentSwitcher />
      </PlaygroundProvider>
    );

    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });
    await waitFor(() => expect(instrumentRenders).toBeGreaterThan(0));

    const instrumentBefore = instrumentRenders;
    expect(lastMoment).toBe('electorate');

    fireEvent.click(screen.getByText('go-method'));
    await act(async () => {
      await Promise.resolve();
    });

    // The journey slice really did change (and its useLayoutEffect swapped
    // the lens to 'criteria' alongside it)...
    expect(lastMoment).toBe('method');
    // ...but the live spatial data didn't, so its consumer wasn't re-rendered.
    expect(instrumentRenders).toBe(instrumentBefore);
  });
});
