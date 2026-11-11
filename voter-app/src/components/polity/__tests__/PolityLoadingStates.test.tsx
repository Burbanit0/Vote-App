import React from 'react';
import { render, screen } from '@testing-library/react';
import MacroCurvesPanel from '../MacroCurvesPanel';
import PopulationMap from '../PopulationMap';
import RunFacts from '../RunFacts';
import TickPlayer from '../TickPlayer';
import type { PolityCtx } from '../PolityController';
import { runOverview } from '../../../test/polityApi';

// The panels are all mounted under the page before a run has loaded (a slow or failed request):
// each must render nothing then, not throw or show half a panel. The page-level tests only ever
// see a loaded run, so this feeds the panels a context directly.

const ctx = vi.hoisted(() => ({ current: {} as unknown as PolityCtx }));
vi.mock('../PolityController', () => ({ usePolityCtx: () => ctx.current }));

// Typed, so a field added to the context breaks this file's build instead of leaving a stale stub.
const base: PolityCtx = {
  runs: undefined,
  runsLoading: true,
  runsError: undefined,
  run: undefined,
  runKey: null,
  setRunKey: vi.fn(),
  overview: undefined,
  overviewLoading: true,
  overviewError: undefined,
  tick: 0,
  setTick: vi.fn(),
  lens: 'activity',
  setLens: vi.fn(),
  citizen: null,
  setCitizen: vi.fn(),
  frame: undefined,
  frameLoading: false,
};

describe('Polity panels before a run has loaded', () => {
  beforeEach(() => {
    ctx.current = { ...base };
  });

  it.each([
    ['the macro curves', MacroCurvesPanel],
    ['the population map', PopulationMap],
    ['the run facts', RunFacts],
    ['the tick player', TickPlayer],
  ] as [string, React.FC][])('%s render nothing', (_name, Panel) => {
    const { container } = render(<Panel />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('RunFacts for a run the list does not carry', () => {
  it('reads the overview alone: no engine, no progress', () => {
    // A run whose summary is not in the list (the list failed, or has moved on) still has its
    // overview: the facts show what the overview says, and "—" for the engine.
    ctx.current = {
      ...base,
      overview: runOverview('gone') as unknown as PolityCtx['overview'], // the fixture is loosely typed
      run: undefined,
      overviewLoading: false,
    };
    render(<RunFacts />);
    expect(screen.getByTestId('polity-fact-engine')).toHaveTextContent('—');
    expect(screen.queryByTestId('polity-fact-status')).not.toBeInTheDocument();
    expect(screen.getByTestId('polity-fact-population')).toBeInTheDocument();
  });
});
