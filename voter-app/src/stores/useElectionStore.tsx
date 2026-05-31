/**
 * useElectionStore — global election config slice (Phase 5.4).
 *
 * Source of truth for the Election Lab config + active scenario metadata
 * (was ElectionContext, the app's spine — ~35 consumers). `stores/useElectionStore`
 * is now a thin shim over this store so every `useElection()` consumer + the
 * <ElectionProvider> in App.tsx keep working until 5.5 deletes the shim.
 *
 * Persistence: localStorage['votelab_election_config'] (written on each mutation,
 * re-read by hydrate() on mount).
 */
import React, { useEffect } from 'react';
import { create } from 'zustand';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ElectionCandidate {
  name: string;
  x:    number;
  y:    number;
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
  description?: string;
  phenomenon?:  string;
}

export interface ScenarioMeta {
  id:          string;
  name:        string;
  description: string;
  phenomenon:  string;
}

const _BLANK_OFF = { enabled: false, rule: 'symbolic' as const, contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' as const } };
const _INFO_OFF  = { enabled: false, media_bias: {}, voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 } };
const _CAMP_OFF  = { enabled: false, num_days: 30, polling_effect: 0.3 };

export const DEFAULT_CONFIG: ElectionConfig = {
  candidates: [
    { name: 'Alice', x: -0.5, y: -0.2 },
    { name: 'Bob',   x:  0.5, y:  0.2 },
    { name: 'Carol', x:  0.0, y:  0.3 },
  ],
  num_voters: 300,
  ideology:   'random',
  seed:       42,
  blank_vote:        _BLANK_OFF,
  information_model: _INFO_OFF,
  campaign:          _CAMP_OFF,
};

// ── Pre-built scenarios ───────────────────────────────────────────────────────

export const SCENARIOS: Record<string, ElectionConfig> = {
  default: DEFAULT_CONFIG,

  france2002: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Chirac',      x:  0.3, y:  0.4 },
      { name: 'Jospin',      x: -0.4, y: -0.3 },
      { name: 'Le Pen',      x:  0.8, y:  0.8 },
      { name: 'Bayrou',      x:  0.1, y:  0.1 },
      { name: 'Chevènement', x: -0.2, y:  0.1 },
      { name: 'Mégret',      x:  0.9, y:  0.9 },
      { name: 'Taubira',     x: -0.7, y: -0.6 },
      { name: 'Besancenot',  x: -0.8, y: -0.5 },
    ],
    num_voters: 500,
    ideology:   'polarized',
    seed:       2002,
    blank_vote: { enabled: true, rule: 'symbolic', contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' } },
    information_model: _INFO_OFF,
    campaign:   { enabled: true, num_days: 30, polling_effect: 0.35 },
    description: 'La gauche fragmentée en 6 candidats élimine Jospin dès le 1er tour, laissant Le Pen en 2e position face à Chirac.',
    phenomenon:  'Paradoxe de Condorcet',
  },

  usa1992: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Clinton', x: -0.2, y: -0.1 },
      { name: 'Bush',    x:  0.4, y:  0.5 },
      { name: 'Perot',   x:  0.1, y:  0.0 },
    ],
    num_voters: 500,
    ideology:   'random',
    seed:       1992,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign:   { enabled: true, num_days: 28, polling_effect: 0.4 },
    description: 'Perot capture 19% des voix en tant que tiers candidat, fragmentant le vote et permettant à Clinton de l\'emporter avec 43%.',
    phenomenon:  'Effet spoiler',
  },

  germany2021: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Scholz (SPD)',   x: -0.1, y: -0.1 },
      { name: 'Laschet (CDU)',  x:  0.2, y:  0.3 },
      { name: 'Baerbock (Verts)', x: -0.3, y: -0.4 },
      { name: 'Lindner (FDP)', x:  0.3, y:  0.0 },
      { name: 'Weidel (AfD)',  x:  0.8, y:  0.7 },
      { name: 'Bartsch (Gauche)', x: -0.7, y: -0.3 },
    ],
    num_voters: 500,
    ideology:   'centrist',
    seed:       2021,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign:   { enabled: true, num_days: 28, polling_effect: 0.3 },
    description: 'Six partis, aucun dépassant 30% — les méthodes consensuelles (Borda, Schulze) avantagent les candidats du centre qui feraient de bons partenaires de coalition.',
    phenomenon:  'Fragmentation & coalition',
  },

  condorcet_cycle: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Alice', x: -0.5, y:  0.3 },
      { name: 'Bob',   x:  0.4, y: -0.2 },
      { name: 'Carol', x:  0.0, y: -0.5 },
    ],
    num_voters: 500,
    ideology:   'polarized',
    seed:       314,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign:   _CAMP_OFF,
    description: 'Configuration artificielle illustrant le cycle d\'Arrow : Alice bat Bob, Bob bat Carol, Carol bat Alice — aucune méthode ne peut s\'appuyer sur un consensus transitif.',
    phenomenon:  'Cycle d\'Arrow (intransitivité)',
  },

  consensus: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Centre',        x:  0.0, y:  0.0 },
      { name: 'Gauche Mod.',   x: -0.3, y: -0.2 },
      { name: 'Droite Mod.',   x:  0.3, y:  0.2 },
    ],
    num_voters: 500,
    ideology:   'centrist',
    seed:       77,
    blank_vote: _BLANK_OFF,
    information_model: _INFO_OFF,
    campaign:   _CAMP_OFF,
    description: 'Le candidat du centre bat les deux autres en duel direct — il est le vainqueur de Condorcet. Toutes les méthodes consensuelles s\'accordent sur ce résultat.',
    phenomenon:  'Consensus parfait (Condorcet)',
  },

  france2022: {
    ...DEFAULT_CONFIG,
    candidates: [
      { name: 'Macron',    x:  0.1, y:  0.2 },
      { name: 'Le Pen',    x:  0.8, y:  0.7 },
      { name: 'Mélenchon', x: -0.8, y: -0.5 },
      { name: 'Zemmour',   x:  0.9, y:  0.9 },
      { name: 'Pécresse',  x:  0.4, y:  0.4 },
    ],
    num_voters: 400,
    ideology:   'polarized',
    seed:       2022,
    blank_vote: { enabled: true, rule: 'competitive', contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' } },
    campaign:   { enabled: true, num_days: 30, polling_effect: 0.4 },
    information_model: { enabled: false, media_bias: {}, voter_segments: { low_info: 0.35, medium_info: 0.45, high_info: 0.2 } },
    description: 'Cinq candidats polarisés, vote blanc activé en mode compétitif, campagne de 30 jours.',
    phenomenon:  'Fragmentation & vote blanc',
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
    blank_vote: { enabled: true, rule: 'competitive', contagion: { enabled: true, beta: 0.4, gamma: 0.08, network: 'watts_strogatz' } },
    campaign:   _CAMP_OFF,
    information_model: _INFO_OFF,
    description: 'Vote blanc contagieux (β=0.4) avec règle compétitive — le vote blanc peut remporter l\'élection.',
    phenomenon:  'Crise constitutionnelle',
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const LS_KEY = 'votelab_election_config';

function deepSet(obj: unknown, path: string, value: unknown): unknown {
  const parts = path.split('.');
  if (parts.length === 1) return { ...(obj as object), [parts[0]]: value };
  const [head, ...rest] = parts;
  const parent = obj as Record<string, unknown>;
  return { ...parent, [head]: deepSet(parent[head] ?? {}, rest.join('.'), value) };
}

function loadConfig(): ElectionConfig {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as ElectionConfig) : DEFAULT_CONFIG;
  } catch {
    return DEFAULT_CONFIG;
  }
}

function saveConfig(config: ElectionConfig): void {
  try { localStorage.setItem(LS_KEY, JSON.stringify(config)); } catch { /* ignore */ }
}

// ── Store ─────────────────────────────────────────────────────────────────

export const SCENARIO_NAMES = Object.keys(SCENARIOS);

interface ElectionState {
  config: ElectionConfig;
  scenarioMeta: ScenarioMeta | null;
  setConfig: (patch: Partial<ElectionConfig>) => void;
  setConfigDeep: (path: string, value: unknown) => void;
  replaceConfig: (next: ElectionConfig) => void;
  resetConfig: () => void;
  applyScenario: (name: string) => void;
  clearScenarioMeta: () => void;
  hydrate: () => void;
}

export const useElectionStore = create<ElectionState>((set) => ({
  config: loadConfig(),
  scenarioMeta: null,

  setConfig: (patch) => set((s) => {
    const config = { ...s.config, ...patch };
    saveConfig(config);
    return { config, scenarioMeta: null };
  }),

  setConfigDeep: (path, value) => set((s) => {
    const config = deepSet(s.config, path, value) as ElectionConfig;
    saveConfig(config);
    return { config, scenarioMeta: null };
  }),

  replaceConfig: (next) => {
    saveConfig(next);
    set({ config: next, scenarioMeta: null });
  },

  resetConfig: () => {
    saveConfig(DEFAULT_CONFIG);
    set({ config: DEFAULT_CONFIG, scenarioMeta: null });
  },

  applyScenario: (name) => {
    const scenario = SCENARIOS[name];
    if (!scenario) return;
    saveConfig(scenario);
    set({
      config: scenario,
      scenarioMeta: scenario.description
        ? { id: name, name, description: scenario.description, phenomenon: scenario.phenomenon ?? '' }
        : null,
    });
  },

  clearScenarioMeta: () => set({ scenarioMeta: null }),

  hydrate: () => set({ config: loadConfig() }),
}));

// ── Convenience hook (former ElectionContext API) ─────────────────────────────

export interface ElectionContextValue {
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

/**
 * Optional provider — the store self-hydrates `config` at module init, so this is
 * only a hydrate-on-mount hook (kept for test isolation + so existing
 * `<ElectionProvider>` wrappers in tests/App keep working). Not required for the
 * store to function.
 */
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
