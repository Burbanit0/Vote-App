import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockRejectedValue(new Error('not under test')),
}));
vi.mock('../../../services/assemblyApi', () => ({
  runAssembly: vi.fn().mockRejectedValue(new Error('not under test')),
  runAssemblyScorecard: vi.fn().mockRejectedValue(new Error('not under test')),
}));

import { PlaygroundProvider, useJourneyCtx } from '../PlaygroundController';
import { ShareScenarioButton, SharedScenarioNotice } from '../ScenarioShare';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';
import { scenarioHash, type ScenarioLink } from '../../../lib/scenarioLink';

// A scenario link opens on mount (and on a hash change), replaces the visitor's scenario, keeps
// theirs for "Back to my scenario", and strips itself from the address. The button writes one.

const mine = {
  ...DEFAULT_CONFIG,
  candidates: [
    { name: 'Mine A', x: -0.1, y: 0 },
    { name: 'Mine B', x: 0.1, y: 0 },
  ],
  description: 'My own scenario',
};

const shared: ScenarioLink = {
  config: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Ana', x: -0.6, y: 0.2 },
      { name: 'Ben', x: 0.6, y: -0.2 },
      { name: 'Cleo', x: 0, y: 0.5 },
    ],
    seed: 11,
  },
  playground: { ...DEFAULT_PLAYGROUND, behavior: 'strategic' },
  rule: 'borda',
  moment: 'method',
  lens: 'probability',
};

const second: ScenarioLink = {
  ...shared,
  config: { ...shared.config, seed: 12 },
  rule: 'irv',
  moment: 'strategy',
  lens: 'winner',
};

const Probe: React.FC = () => {
  const { activeMoment, leaderRule, lens, setActiveMoment, setLeaderRule, setLens } =
    useJourneyCtx();
  return (
    <div>
      <span data-testid="probe">{`${activeMoment}/${leaderRule}/${lens}`}</span>
      <button data-testid="to-bilan" onClick={() => setActiveMoment('bilan')} />
      <button data-testid="to-approval" onClick={() => setLeaderRule('approval')} />
      <button data-testid="to-manipulation" onClick={() => setLens('manipulation')} />
    </div>
  );
};

const mount = () =>
  render(
    <PlaygroundProvider>
      <Probe />
      <ShareScenarioButton />
      <SharedScenarioNotice />
    </PlaygroundProvider>
  );

const probe = () => screen.getByTestId('probe').textContent;
const names = () => useElectionStore.getState().config.candidates.map((c) => c.name);
const openByHash = (link: ScenarioLink) => {
  act(() => {
    window.location.hash = scenarioHash(link);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
};

const umami = vi.fn();

beforeEach(() => {
  umami.mockReset();
  (window as { umami?: unknown }).umami = { track: umami };
  localStorage.clear();
  window.history.replaceState(null, '', '/playground');
  useElectionStore.setState({
    config: mine,
    playground: { ...DEFAULT_PLAYGROUND },
    scenarioMeta: null,
  });
});

describe('opening a scenario link', () => {
  it('does nothing without a link: the visitor keeps their scenario and no notice shows', () => {
    mount();
    expect(names()).toEqual(['Mine A', 'Mine B']);
    expect(probe()).toBe('electorate/plurality/winner');
    expect(screen.queryByTestId('shared-scenario-notice')).toBeNull();
  });

  it('applies the config, the playground, the rule, the moment and the lens, and shows the notice', () => {
    window.history.replaceState(null, '', `/playground?x=1${scenarioHash(shared)}`);
    mount();
    expect(names()).toEqual(['Ana', 'Ben', 'Cleo']);
    expect(useElectionStore.getState().config.seed).toBe(11);
    expect(useElectionStore.getState().playground.behavior).toBe('strategic');
    // The lens is the link's, not the Méthode moment's own default ('criteria').
    expect(probe()).toBe('method/borda/probability');
    expect(screen.getByTestId('shared-scenario-notice')).toBeInTheDocument();
  });

  it('takes the link lens when the moment is the one already open', () => {
    window.history.replaceState(
      null,
      '',
      `/playground${scenarioHash({ ...shared, moment: 'electorate', lens: 'manipulation' })}`
    );
    mount();
    expect(probe()).toBe('electorate/borda/manipulation');
  });

  it('removes the link from the address, and keeps the rest of it', () => {
    window.history.replaceState(null, '', `/playground?story=x${scenarioHash(shared)}`);
    mount();
    expect(window.location.hash).toBe('');
    expect(window.location.pathname + window.location.search).toBe('/playground?story=x');
  });

  it('keeps the history state of the page, which the router keeps its place in', () => {
    window.history.replaceState({ idx: 3 }, '', `/playground${scenarioHash(shared)}`);
    mount();
    expect(window.history.state).toEqual({ idx: 3 });
    expect(window.location.hash).toBe('');
  });

  it('a description the link does not have is not inherited from the visitor scenario', () => {
    window.history.replaceState(null, '', `/playground${scenarioHash(shared)}`);
    mount();
    expect(useElectionStore.getState().config.description).toBeUndefined();
  });

  it('ignores a hash that is not a scenario', () => {
    window.history.replaceState(null, '', '/playground#section');
    mount();
    expect(names()).toEqual(['Mine A', 'Mine B']);
    expect(window.location.hash).toBe('#section');
    expect(screen.queryByTestId('shared-scenario-notice')).toBeNull();
  });

  it('opens a link pasted into the tab that is already open', () => {
    mount();
    openByHash(shared);
    expect(names()).toEqual(['Ana', 'Ben', 'Cleo']);
    expect(probe()).toBe('method/borda/probability');
    expect(screen.getByTestId('shared-scenario-notice')).toBeInTheDocument();
  });

  it('stops listening for hash changes when the page is left', () => {
    const view = mount();
    view.unmount();
    openByHash(shared);
    expect(names()).toEqual(['Mine A', 'Mine B']);
  });
});

describe('opening a scenario link, measured', () => {
  it('records one event per link opened, with nothing about the scenario', () => {
    mount();
    expect(umami).not.toHaveBeenCalled();
    openByHash(shared);
    expect(umami).toHaveBeenCalledTimes(1);
    expect(umami).toHaveBeenCalledWith('scenario_link_opened', undefined);
  });
});

describe('the lens of a link', () => {
  it('is for the moment of the link only: the next moment has its own default lens', () => {
    mount();
    openByHash(shared);
    expect(probe()).toBe('method/borda/probability');
    fireEvent.click(screen.getByTestId('to-bilan'));
    expect(probe()).toBe('bilan/borda/winner');
  });
});

describe('Back to my scenario', () => {
  it('puts back the lens the visitor had chosen, in the moment the link also opened on', () => {
    mount();
    fireEvent.click(screen.getByTestId('to-manipulation'));
    openByHash({ ...shared, moment: 'electorate', lens: 'criteria' });
    expect(probe()).toBe('electorate/borda/criteria');
    fireEvent.click(screen.getByTestId('shared-scenario-restore'));
    expect(probe()).toBe('electorate/plurality/manipulation');
  });

  it('puts back the lens the visitor had chosen, in another moment', () => {
    mount();
    fireEvent.click(screen.getByTestId('to-bilan'));
    fireEvent.click(screen.getByTestId('to-manipulation'));
    openByHash(shared);
    fireEvent.click(screen.getByTestId('shared-scenario-restore'));
    expect(probe()).toBe('bilan/plurality/manipulation');
  });

  it('puts back the scenario, the rule and the moment the visitor had, and closes the notice', () => {
    mount();
    fireEvent.click(screen.getByTestId('to-bilan'));
    fireEvent.click(screen.getByTestId('to-approval'));
    openByHash(shared);
    fireEvent.click(screen.getByTestId('shared-scenario-restore'));
    expect(names()).toEqual(['Mine A', 'Mine B']);
    expect(useElectionStore.getState().config.description).toBe('My own scenario');
    expect(useElectionStore.getState().playground.behavior).toBe(DEFAULT_PLAYGROUND.behavior);
    expect(probe()).toBe('bilan/approval/winner');
    expect(screen.queryByTestId('shared-scenario-notice')).toBeNull();
  });

  it('goes back to the visitor scenario, not to the first link, after a second link', () => {
    mount();
    openByHash(shared);
    openByHash(second);
    expect(useElectionStore.getState().config.seed).toBe(12);
    fireEvent.click(screen.getByTestId('shared-scenario-restore'));
    expect(names()).toEqual(['Mine A', 'Mine B']);
    expect(probe()).toBe('electorate/plurality/winner');
  });

  it('puts back a visitor scenario that had no description over one that had', () => {
    useElectionStore.setState({ config: { ...mine, description: undefined } });
    mount();
    openByHash({ ...shared, config: { ...shared.config, description: 'Theirs' } });
    expect(useElectionStore.getState().config.description).toBe('Theirs');
    fireEvent.click(screen.getByTestId('shared-scenario-restore'));
    expect(useElectionStore.getState().config.description).toBeUndefined();
  });
});

describe('Keep this one', () => {
  it('closes the notice and leaves the scenario from the link in place', () => {
    mount();
    openByHash(shared);
    fireEvent.click(screen.getByTestId('shared-scenario-keep'));
    expect(screen.queryByTestId('shared-scenario-notice')).toBeNull();
    expect(names()).toEqual(['Ana', 'Ben', 'Cleo']);
  });
});

describe('Share this scenario', () => {
  const writeText = vi.fn();
  beforeEach(() => {
    writeText.mockReset();
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
  });

  it('copies a link to the scenario on screen, and says so for a moment', async () => {
    vi.useFakeTimers();
    try {
      writeText.mockResolvedValue(undefined);
      mount();
      fireEvent.click(screen.getByTestId('to-bilan'));
      await act(async () => {
        fireEvent.click(screen.getByTestId('share-scenario'));
      });
      const url = writeText.mock.calls[0][0] as string;
      expect(url.startsWith(`${window.location.origin}/playground#s=`)).toBe(true);
      expect(screen.getByTestId('share-scenario')).toHaveTextContent('Link copied');
      expect(screen.queryByTestId('share-scenario-manual')).toBeNull();
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(screen.getByTestId('share-scenario')).toHaveTextContent('Share this scenario');
    } finally {
      vi.useRealTimers();
    }
  });

  it('writes a link that opens as the scenario it was made from', async () => {
    writeText.mockResolvedValue(undefined);
    mount();
    fireEvent.click(screen.getByTestId('to-approval'));
    fireEvent.click(screen.getByTestId('to-bilan'));
    fireEvent.click(screen.getByTestId('to-manipulation'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('share-scenario'));
    });
    expect(umami).toHaveBeenCalledWith('scenario_shared', undefined);
    const url = new URL(writeText.mock.calls[0][0] as string);
    useElectionStore.setState({ config: DEFAULT_CONFIG });
    openByHash({ ...shared, rule: 'plurality' }); // something else on screen first
    act(() => {
      window.location.hash = url.hash;
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(names()).toEqual(['Mine A', 'Mine B']);
    expect(probe()).toBe('bilan/approval/manipulation');
  });

  it('shows the link in a field to copy by hand when the clipboard refuses', async () => {
    writeText.mockRejectedValue(new Error('denied'));
    mount();
    await act(async () => {
      fireEvent.click(screen.getByTestId('share-scenario'));
    });
    const field = screen.getByTestId('share-scenario-manual') as HTMLInputElement;
    expect(field.value).toContain('#s=');
    expect(field).toHaveAttribute('readonly');
    expect(screen.getByTestId('share-scenario')).toHaveTextContent('Share this scenario');
    const select = vi.spyOn(field, 'select');
    fireEvent.focus(field);
    expect(select).toHaveBeenCalled();
  });

  it('hides that field once a later copy works', async () => {
    writeText.mockRejectedValueOnce(new Error('denied')).mockResolvedValue(undefined);
    mount();
    await act(async () => {
      fireEvent.click(screen.getByTestId('share-scenario'));
    });
    expect(screen.getByTestId('share-scenario-manual')).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByTestId('share-scenario'));
    });
    expect(screen.queryByTestId('share-scenario-manual')).toBeNull();
  });
});
