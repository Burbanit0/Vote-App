import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// PlaygroundProvider pulls in the live-diagnostics hook, which debounces a call to profileApi,
// and (in parliament mode) the assembly endpoints: neither is under test here.
vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockRejectedValue(new Error('not under test')),
}));
vi.mock('../../../services/assemblyApi', () => ({
  runAssembly: vi.fn().mockRejectedValue(new Error('not under test')),
  runAssemblyScorecard: vi.fn().mockRejectedValue(new Error('not under test')),
}));

import { PlaygroundProvider, useInstrumentCtx } from '../PlaygroundController';
import StrategyMoment from '../moments/StrategyMoment';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';

// The "Vous" diamond on the map is a voter of your own. In the Stratégie moment it used to move
// and change nothing: its only reader was the sincerity fiche, which lives in the Lab. This is the
// panel that gives it a meaning, so what is pinned here is the contract: it ships closed (the
// playground's form-lock: nothing heavy at first paint), it reads the SAME position the map marker
// drags, and it only exists for the single-winner question.

let youApi: ReturnType<typeof useInstrumentCtx> | null = null;
const YouProbe: React.FC = () => {
  youApi = useInstrumentCtx();
  return null;
};

function mount() {
  render(
    <PlaygroundProvider>
      <StrategyMoment />
      <YouProbe />
    </PlaygroundProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
  youApi = null;
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG },
    playground: { ...DEFAULT_PLAYGROUND },
    scenarioMeta: null,
  });
});

describe('StrategyMoment: the "Vous" panel', () => {
  it('ships closed: the sincerity module is not mounted until it is opened', () => {
    mount();
    expect(screen.getByTestId('module-sincerity-toggle')).toBeInTheDocument();
    expect(screen.queryByTestId('sincerity-module')).not.toBeInTheDocument();
  });

  it('opens on a click and judges the methods for the shared "you" position', () => {
    mount();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    expect(screen.getByTestId('sincerity-module')).toBeInTheDocument();
    expect(screen.getByTestId('sincerity-headline')).toBeInTheDocument();
    expect(screen.getByTestId('sincerity-you-x')).toHaveValue(String(youApi!.youPos.x));
  });

  it('follows the diamond: moving "you" on the map moves the sliders and the verdicts', async () => {
    mount();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    const order = () => screen.getByTestId('sincerity-order').textContent;
    act(() => youApi!.setYouPos({ x: -0.9, y: 0.1, z: 0 }));
    await waitFor(() => expect(screen.getByTestId('sincerity-you-x')).toHaveValue('-0.9'));
    const left = order();
    act(() => youApi!.setYouPos({ x: 0.9, y: 0.1, z: 0 }));
    await waitFor(() => expect(screen.getByTestId('sincerity-you-x')).toHaveValue('0.9'));
    // Your sincere order of the candidates is read off your position, not off the slider label:
    // the far-left and far-right voter rank the same three candidates in opposite orders.
    expect(order()).not.toBe(left);
  });

  it('the sliders move the same position the map marker uses', async () => {
    mount();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    fireEvent.change(screen.getByTestId('sincerity-you-x'), { target: { value: '0.5' } });
    await waitFor(() => expect(youApi!.youPos.x).toBeCloseTo(0.5));
  });

  it('says so when there are fewer than three candidates (no dilemma is possible)', () => {
    useElectionStore.setState({
      config: { ...DEFAULT_CONFIG, candidates: DEFAULT_CONFIG.candidates.slice(0, 2) },
    });
    mount();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    expect(screen.getByTestId('sincerity-few')).toBeInTheDocument();
  });

  it('says nothing of the kind with three or more', () => {
    mount();
    fireEvent.click(screen.getByTestId('module-sincerity-toggle'));
    expect(screen.queryByTestId('sincerity-few')).not.toBeInTheDocument();
  });

  it('is not offered for a non-spatial preference source: there is no diamond to drag', () => {
    useElectionStore.setState({
      playground: { ...DEFAULT_PLAYGROUND, prefSource: 'impartial' },
    });
    mount();
    expect(screen.queryByTestId('module-sincerity-toggle')).not.toBeInTheDocument();
  });

  it('is only offered for the single-winner question, not the assembly', () => {
    useElectionStore.setState({
      playground: { ...DEFAULT_PLAYGROUND, mode: 'parliament' },
    });
    mount();
    expect(screen.queryByTestId('module-sincerity-toggle')).not.toBeInTheDocument();
  });
});
