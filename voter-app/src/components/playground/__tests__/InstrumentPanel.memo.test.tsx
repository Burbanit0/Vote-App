import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Same mock as PlaygroundController.render.test.tsx — PlaygroundProvider pulls
// in the live-diagnostics hook, which debounces a call to profileApi.
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

import * as playgroundVoting from '../../../lib/playgroundVoting';
import {
  PlaygroundProvider,
  useScorecardCtx,
  useJourneyCtx,
  useInstrumentCtx,
} from '../PlaygroundController';
import InstrumentPanel from '../InstrumentPanel';

// This is the end-to-end counterpart to LeaderCanvas.test.tsx's `React.memo`
// block: that file proves the memo mechanism itself works when FED stable
// props by hand; this file proves the REAL wiring (InstrumentPanel's actual
// JSX call site, through the real PlaygroundProvider) actually PASSES stable
// props end to end. It's the one that would have caught the landmine this PR
// found and fixed: InstrumentPanel used to pass `onMoveYou={(x, y) =>
// setYouPos(...)}` as a fresh inline closure on every render — a memo
// boundary alone can't catch that; only a test exercising the real call site
// can. `fieldWinnerName` (see LeaderCanvas.test.tsx for why it's a reliable
// proxy for "did LeaderCanvas's render body actually execute") is spied on
// here the same way.
//
// The trigger is `setLensMode` (scorecardCtx) — a field InstrumentPanel reads
// (broad usePlaygroundCtx()) but that feeds into NONE of LeaderCanvas's props
// (lensMode/dial only drive `effectiveWeights`, read by the Bilan/values
// lens, not the map). So InstrumentPanel legitimately re-renders on this
// change (it's on the broad context by design, see PlaygroundController.tsx),
// while LeaderCanvas — now memoized — must not.
function LensModeToggler() {
  const { lensMode, setLensMode } = useScorecardCtx();
  return (
    <button onClick={() => setLensMode(lensMode === 'dial' ? 'granular' : 'dial')}>
      toggle-lens-mode
    </button>
  );
}

describe('InstrumentPanel → LeaderCanvas memo wiring', () => {
  it('LeaderCanvas does not re-render when an unrelated scorecardCtx field changes', async () => {
    const spy = vi.spyOn(playgroundVoting, 'fieldWinnerName');

    render(
      <PlaygroundProvider>
        <InstrumentPanel />
        <LensModeToggler />
      </PlaygroundProvider>
    );

    await waitFor(() => expect(screen.getByTestId('leader-canvas')).toBeInTheDocument());
    // Let the debounced live-diagnostics call (350ms) resolve so its setState
    // doesn't land inside the measurement window below (same settle pattern as
    // PlaygroundController.render.test.tsx).
    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });

    const rendersBeforeToggle = spy.mock.calls.length;
    expect(rendersBeforeToggle).toBeGreaterThan(0);

    fireEvent.click(screen.getByText('toggle-lens-mode'));
    await act(async () => {
      await Promise.resolve();
    });

    // InstrumentPanel itself DID re-render (it's on the broad context on
    // purpose)... but LeaderCanvas's own props never changed, so its memo
    // boundary must have bailed.
    expect(spy.mock.calls).toHaveLength(rendersBeforeToggle);
  });

  it('LeaderCanvas DOES re-render when a candidate is dragged (a real, relevant prop change)', async () => {
    const spy = vi.spyOn(playgroundVoting, 'fieldWinnerName');

    render(
      <PlaygroundProvider>
        <InstrumentPanel />
      </PlaygroundProvider>
    );

    await waitFor(() => expect(screen.getByTestId('leader-canvas')).toBeInTheDocument());
    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });

    const rendersBeforeDrag = spy.mock.calls.length;

    // Drag a candidate — this is exactly moveCandidate's real path (mousedown
    // then a window mousemove), the one Finding A/B are both about.
    fireEvent.mouseDown(screen.getByTestId('candidate-0'));
    fireEvent.mouseMove(window, { clientX: 250, clientY: 200 });

    expect(spy.mock.calls.length).toBeGreaterThan(rendersBeforeDrag);
  });

  it('dragging the "you" marker calls through the real onMoveYou -> moveYou wiring', async () => {
    // Exercises moveYou's actual body (PlaygroundController.tsx), not just its
    // creation -- the previous two tests never drag the you-marker, so without
    // this the hoisted callback's own call to setYouPos would be unexercised.
    function MomentSwitcher() {
      const { setActiveMoment } = useJourneyCtx();
      React.useEffect(() => {
        setActiveMoment('strategy'); // showYou = mode 'leader' && moment 'strategy'
      }, [setActiveMoment]);
      return null;
    }
    function YouPosReadout() {
      const { youPos } = useInstrumentCtx();
      return <span data-testid="you-x">{youPos.x.toFixed(2)}</span>;
    }

    render(
      <PlaygroundProvider>
        <MomentSwitcher />
        <InstrumentPanel />
        <YouPosReadout />
      </PlaygroundProvider>
    );

    await waitFor(() => expect(screen.getByTestId('you-marker')).toBeInTheDocument());
    const before = screen.getByTestId('you-x').textContent;

    fireEvent.mouseDown(screen.getByTestId('you-marker'));
    fireEvent.mouseMove(window, { clientX: 300, clientY: 200 });

    await waitFor(() => expect(screen.getByTestId('you-x').textContent).not.toBe(before));
  });
});
