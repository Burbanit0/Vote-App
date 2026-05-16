import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ElectionCandidate {
  name: string;
  x:    number;  // economy axis [-1, 1]
  y:    number;  // social axis  [-1, 1]
}

export interface ElectionConfig {
  candidates: ElectionCandidate[];
  num_voters: number;
  ideology:   string;
  seed:       number;

  blank_vote: {
    enabled:   boolean;
    rule:      'symbolic' | 'competitive' | 'threshold_30';
    contagion: {
      enabled: boolean;
      beta:    number;
      gamma:   number;
      network: 'random' | 'watts_strogatz' | 'block';
    };
  };

  information_model: {
    enabled:        boolean;
    media_bias:     Record<string, number>;
    voter_segments: { low_info: number; medium_info: number; high_info: number };
  };

  campaign: {
    enabled:        boolean;
    num_days:       number;
    polling_effect: number;
  };
}

const DEFAULT_CONFIG: ElectionConfig = {
  candidates: [
    { name: 'Alice', x: -0.5, y: -0.2 },
    { name: 'Bob',   x:  0.5, y:  0.2 },
    { name: 'Carol', x:  0.0, y:  0.3 },
  ],
  num_voters: 300,
  ideology:   'random',
  seed:       42,

  blank_vote: {
    enabled:   false,
    rule:      'symbolic',
    contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' },
  },

  information_model: {
    enabled:        false,
    media_bias:     {},
    voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
  },

  campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
};

// ── Pre-built scenarios ───────────────────────────────────────────────────────

const SCENARIOS: Record<string, ElectionConfig> = {
  default: DEFAULT_CONFIG,

  france2022: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Macron',     x:  0.1, y:  0.2 },
      { name: 'Le Pen',     x:  0.8, y:  0.7 },
      { name: 'Mélenchon',  x: -0.8, y: -0.5 },
      { name: 'Zemmour',    x:  0.9, y:  0.9 },
      { name: 'Pécresse',   x:  0.4, y:  0.4 },
    ],
    num_voters: 400,
    ideology:   'polarized',
    seed:       2022,
    blank_vote: {
      enabled:   true,
      rule:      'competitive',
      contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' },
    },
    campaign: { enabled: true, num_days: 30, polling_effect: 0.4 },
    information_model: {
      enabled: false,
      media_bias: {},
      voter_segments: { low_info: 0.35, medium_info: 0.45, high_info: 0.2 },
    },
  },

  crisis: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Alice', x: -0.6, y: -0.3 },
      { name: 'Bob',   x:  0.6, y:  0.3 },
      { name: 'Carol', x:  0.0, y:  0.5 },
    ],
    num_voters: 300,
    ideology:   'polarized',
    seed:       99,
    blank_vote: {
      enabled:   true,
      rule:      'competitive',
      contagion: { enabled: true, beta: 0.4, gamma: 0.08, network: 'watts_strogatz' },
    },
    campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
    information_model: { enabled: false, media_bias: {}, voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 } },
  },

  consensus: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Alice', x: -0.2, y:  0.1 },
      { name: 'Bob',   x:  0.3, y:  0.0 },
      { name: 'Carol', x: -0.1, y: -0.2 },
    ],
    num_voters: 300,
    ideology:   'centrist',
    seed:       77,
    blank_vote: { enabled: false, rule: 'symbolic', contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' } },
    campaign: { enabled: false, num_days: 14, polling_effect: 0.2 },
    information_model: { enabled: false, media_bias: {}, voter_segments: { low_info: 0.2, medium_info: 0.6, high_info: 0.2 } },
  },
};

// ── Context value ─────────────────────────────────────────────────────────────

interface ElectionContextValue {
  config:          ElectionConfig;
  setConfig:       (patch: Partial<ElectionConfig>) => void;
  setConfigDeep:   (path: string, value: unknown) => void;
  resetConfig:     () => void;
  applyScenario:   (name: string) => void;
  scenarioNames:   string[];
}

const ElectionContext = createContext<ElectionContextValue>({
  config:        DEFAULT_CONFIG,
  setConfig:     () => {},
  setConfigDeep: () => {},
  resetConfig:   () => {},
  applyScenario: () => {},
  scenarioNames: Object.keys(SCENARIOS),
});

export function useElection(): ElectionContextValue {
  return useContext(ElectionContext);
}

// ── Deep-set helper ───────────────────────────────────────────────────────────

function deepSet(obj: unknown, path: string, value: unknown): unknown {
  const parts = path.split('.');
  if (parts.length === 1) return { ...(obj as object), [parts[0]]: value };
  const [head, ...rest] = parts;
  const parent = obj as Record<string, unknown>;
  return { ...parent, [head]: deepSet(parent[head] ?? {}, rest.join('.'), value) };
}

// ── Provider ──────────────────────────────────────────────────────────────────

const LS_KEY = 'votelab_election_config';

export const ElectionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [config, setConfigState] = useState<ElectionConfig>(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      return raw ? (JSON.parse(raw) as ElectionConfig) : DEFAULT_CONFIG;
    } catch {
      return DEFAULT_CONFIG;
    }
  });

  // Persist on every change
  useEffect(() => {
    try { localStorage.setItem(LS_KEY, JSON.stringify(config)); } catch {}
  }, [config]);

  const setConfig = useCallback((patch: Partial<ElectionConfig>) => {
    setConfigState((prev) => ({ ...prev, ...patch }));
  }, []);

  const setConfigDeep = useCallback((path: string, value: unknown) => {
    setConfigState((prev) => deepSet(prev, path, value) as ElectionConfig);
  }, []);

  const resetConfig = useCallback(() => setConfigState(DEFAULT_CONFIG), []);

  const applyScenario = useCallback((name: string) => {
    if (SCENARIOS[name]) setConfigState(SCENARIOS[name]);
  }, []);

  return (
    <ElectionContext.Provider value={{
      config, setConfig, setConfigDeep, resetConfig,
      applyScenario, scenarioNames: Object.keys(SCENARIOS),
    }}>
      {children}
    </ElectionContext.Provider>
  );
};
