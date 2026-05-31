/**
 * ElectionContext — compatibility shim over useElectionStore (Phase 5.4).
 *
 * The global election config + scenario logic now lives in
 * stores/useElectionStore. This keeps useElection()/ElectionProvider + the
 * exported types working for the ~35 consumers until 5.5 deletes the shim.
 */
import React, { useEffect } from 'react';
import {
  useElectionStore,
  SCENARIO_NAMES,
  type ElectionConfig,
  type ElectionCandidate,
  type ScenarioMeta,
} from '../stores/useElectionStore';

export type { ElectionConfig, ElectionCandidate, ScenarioMeta };

interface ElectionContextValue {
  config:            ElectionConfig;
  setConfig:         (patch: Partial<ElectionConfig>) => void;
  setConfigDeep:     (path: string, value: unknown) => void;
  replaceConfig:     (next: ElectionConfig) => void;
  resetConfig:       () => void;
  applyScenario:     (name: string) => void;
  scenarioNames:     string[];
  scenarioMeta:      ScenarioMeta | null;
  clearScenarioMeta: () => void;
}

export const ElectionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydrate = useElectionStore((s) => s.hydrate);
  useEffect(() => { hydrate(); }, [hydrate]);
  return <>{children}</>;
};

export function useElection(): ElectionContextValue {
  const config = useElectionStore((s) => s.config);
  const setConfig = useElectionStore((s) => s.setConfig);
  const setConfigDeep = useElectionStore((s) => s.setConfigDeep);
  const replaceConfig = useElectionStore((s) => s.replaceConfig);
  const resetConfig = useElectionStore((s) => s.resetConfig);
  const applyScenario = useElectionStore((s) => s.applyScenario);
  const scenarioMeta = useElectionStore((s) => s.scenarioMeta);
  const clearScenarioMeta = useElectionStore((s) => s.clearScenarioMeta);
  return {
    config, setConfig, setConfigDeep, replaceConfig, resetConfig,
    applyScenario, scenarioNames: SCENARIO_NAMES, scenarioMeta, clearScenarioMeta,
  };
}
