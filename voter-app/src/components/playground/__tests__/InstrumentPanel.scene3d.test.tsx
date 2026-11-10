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

import { PlaygroundProvider } from '../PlaygroundController';
import InstrumentPanel from '../InstrumentPanel';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';

// LeaderCanvas.test.tsx and LeaderScene3D.test.tsx feed the scene props by hand. This is
// the other half: the REAL controller (rule selector, z sliders, store) driving the scene
// through InstrumentPanel's actual call site, so a parameter that stops reaching the 3D
// scene — the failure this file guards — shows up here and not only in a browser.

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG },
    playground: {
      ...DEFAULT_PLAYGROUND,
      space: { dims: 3, axisLabels: ['x', 'y', 'z'], valenceEnabled: false },
    },
    scenarioMeta: null,
  });
});

async function mount() {
  render(
    <PlaygroundProvider>
      <InstrumentPanel forceShowRuleUi />
    </PlaygroundProvider>
  );
  await waitFor(() => expect(screen.getByTestId('scene-3d')).toBeInTheDocument());
  // Let the debounced live-diagnostics call settle before measuring anything.
  await act(async () => {
    await new Promise((r) => setTimeout(r, 500));
  });
}

const readout = () => screen.getByTestId('field-winner').querySelector('strong')!.textContent!;

describe('InstrumentPanel → 3D scene', () => {
  it('the ring follows the winner the controller reports, whichever rule is selected', async () => {
    await mount();
    for (const rule of ['plurality', 'borda', 'irv', 'condorcet', 'two_round']) {
      fireEvent.change(screen.getByTestId('rule-select'), { target: { value: rule } });
      await waitFor(() =>
        expect(screen.getByTestId('scene-winner').parentElement).toHaveTextContent(readout())
      );
    }
  });

  it('a lottery rule rings nobody', async () => {
    await mount();
    fireEvent.change(screen.getByTestId('rule-select'), { target: { value: 'random_ballot' } });
    await waitFor(() => expect(screen.queryByTestId('scene-winner')).not.toBeInTheDocument());
  });

  it('a candidate depth slider moves that candidate in the scene', async () => {
    await mount();
    fireEvent.click(screen.getByTestId('scene-spin')); // freeze the camera
    const circle = () => screen.getByTestId('scene-candidate-0').querySelector('circle')!;
    const place = () => [circle().getAttribute('cx'), circle().getAttribute('cy')].join(',');
    const before = place();
    fireEvent.change(screen.getByTestId('z-slider-0'), { target: { value: '0.9' } });
    await waitFor(() => expect(place()).not.toBe(before));
    expect(screen.getByTestId('z-slider-0')).toHaveValue('0.9');
  });
});
