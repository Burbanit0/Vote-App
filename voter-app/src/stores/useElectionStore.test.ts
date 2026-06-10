import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { ElectionProvider, useElection } from './useElectionStore';

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(ElectionProvider, null, children);
}

beforeEach(() => {
  localStorage.clear();
});

describe('ElectionContext — historical scenarios', () => {
  it('applyScenario("france2002") loads 8 candidates', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('france2002');
    });
    expect(result.current.config.candidates).toHaveLength(8);
    expect(result.current.config.candidates.map((c) => c.name)).toContain('Chirac');
    expect(result.current.config.candidates.map((c) => c.name)).toContain('Jospin');
  });

  it('applyScenario("usa1992") loads 3 candidates', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('usa1992');
    });
    expect(result.current.config.candidates).toHaveLength(3);
    expect(result.current.config.candidates.map((c) => c.name)).toContain('Clinton');
    expect(result.current.config.candidates.map((c) => c.name)).toContain('Perot');
  });

  it('applyScenario("germany2021") loads 6 candidates', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('germany2021');
    });
    expect(result.current.config.candidates).toHaveLength(6);
  });

  it('condorcet_cycle has ideology="polarized"', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('condorcet_cycle');
    });
    expect(result.current.config.ideology).toBe('polarized');
    expect(result.current.config.candidates).toHaveLength(3);
  });

  it('consensus has ideology="centrist"', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('consensus');
    });
    expect(result.current.config.ideology).toBe('centrist');
    expect(result.current.config.candidates).toHaveLength(3);
  });

  it('applyScenario sets scenarioMeta with description and phenomenon', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('france2002');
    });
    expect(result.current.scenarioMeta).not.toBeNull();
    expect(result.current.scenarioMeta?.id).toBe('france2002');
    expect(result.current.scenarioMeta?.phenomenon).toBe('Paradoxe de Condorcet');
    expect(result.current.scenarioMeta?.description.length).toBeGreaterThan(10);
  });

  it('setConfig clears scenarioMeta (manual change)', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('france2002');
    });
    expect(result.current.scenarioMeta).not.toBeNull();

    act(() => {
      result.current.setConfig({ num_voters: 99 });
    });
    expect(result.current.scenarioMeta).toBeNull();
  });

  it('setConfigDeep clears scenarioMeta', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('usa1992');
    });
    act(() => {
      result.current.setConfigDeep('campaign.num_days', 21);
    });
    expect(result.current.scenarioMeta).toBeNull();
  });

  it('clearScenarioMeta removes metadata without changing config', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    act(() => {
      result.current.applyScenario('usa1992');
    });
    const configBefore = result.current.config;
    act(() => {
      result.current.clearScenarioMeta();
    });
    expect(result.current.scenarioMeta).toBeNull();
    expect(result.current.config).toEqual(configBefore);
  });

  it('all historical scenarios have description and phenomenon', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    const historicalIds = ['france2002', 'usa1992', 'germany2021', 'condorcet_cycle'];
    for (const id of historicalIds) {
      act(() => {
        result.current.applyScenario(id);
      });
      expect(result.current.config.description?.length).toBeGreaterThan(5);
      expect(result.current.config.phenomenon?.length).toBeGreaterThan(2);
    }
  });

  it('scenarioNames includes all new historical scenarios', () => {
    const { result } = renderHook(() => useElection(), { wrapper });
    const names = result.current.scenarioNames;
    expect(names).toContain('france2002');
    expect(names).toContain('usa1992');
    expect(names).toContain('germany2021');
    expect(names).toContain('condorcet_cycle');
  });
});
