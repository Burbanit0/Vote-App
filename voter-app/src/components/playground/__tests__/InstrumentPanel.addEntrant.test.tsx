import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockRejectedValue(new Error('not under test')),
}));
vi.mock('../../../services/assemblyApi', () => ({
  runAssembly: vi.fn().mockRejectedValue(new Error('not under test')),
  runAssemblyScorecard: vi.fn().mockRejectedValue(new Error('not under test')),
}));

import { PlaygroundProvider } from '../PlaygroundController';
import InstrumentPanel from '../InstrumentPanel';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';
import { MAX_CANDIDATES } from '../../../lib/candidateEditing';

// A double-click on an empty spot of the leader map adds an entrant there, under the editor's
// rules: a name no one has, and no more than MAX_CANDIDATES.

const candidates = () => useElectionStore.getState().config.candidates;

function mount() {
  render(
    <PlaygroundProvider>
      <InstrumentPanel />
    </PlaygroundProvider>
  );
  const map = screen.getByTestId('leader-map');
  vi.spyOn(map, 'getBoundingClientRect').mockReturnValue({
    left: 0,
    top: 0,
    width: 460,
    height: 460,
    right: 460,
    bottom: 460,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  });
  return map;
}

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG },
    playground: { ...DEFAULT_PLAYGROUND, mode: 'leader' },
    scenarioMeta: null,
  });
});

describe('InstrumentPanel — double-click on the map adds an entrant', () => {
  it('appends a named candidate at the clicked point, in the shared config', () => {
    const map = mount();
    fireEvent.doubleClick(map, { clientX: 345, clientY: 115 });
    expect(candidates()).toHaveLength(4);
    const added = candidates()[3];
    expect(added.name).toBe('Candidate 4');
    expect(added.x).toBeGreaterThan(0);
    expect(added.y).toBeGreaterThan(0);
  });

  it('gives each entrant a name no one has', () => {
    const map = mount();
    fireEvent.doubleClick(map, { clientX: 100, clientY: 100 });
    fireEvent.doubleClick(map, { clientX: 200, clientY: 300 });
    const names = candidates().map((c) => c.name);
    expect(new Set(names).size).toBe(names.length);
    expect(names.slice(3)).toEqual(['Candidate 4', 'Candidate 5']);
  });

  it(`adds nobody past ${MAX_CANDIDATES} candidates`, () => {
    const map = mount();
    for (let i = 0; i < MAX_CANDIDATES + 3; i++) {
      fireEvent.doubleClick(map, { clientX: 20 + i * 30, clientY: 40 + i * 20 });
    }
    expect(candidates()).toHaveLength(MAX_CANDIDATES);
  });
});
