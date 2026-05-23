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

  // Display metadata — ignored by the backend
  description?: string;
  phenomenon?:  string;
}

const _BLANK_OFF = { enabled: false, rule: 'symbolic' as const, contagion: { enabled: false, beta: 0.15, gamma: 0.1, network: 'random' as const } };
const _INFO_OFF  = { enabled: false, media_bias: {}, voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 } };
const _CAMP_OFF  = { enabled: false, num_days: 30, polling_effect: 0.3 };

const DEFAULT_CONFIG: ElectionConfig = {
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

const SCENARIOS: Record<string, ElectionConfig> = {
  default: DEFAULT_CONFIG,

  // ── Historical: France 1er tour 2002 ──────────────────────────────────────
  // Phénomène : la gauche fragmentée en 6 candidats élimine Jospin
  // (préféré par la majorité) au profit de Le Pen. Condorcet paradox classique.
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

  // ── Historical: USA 1992 ─────────────────────────────────────────────────
  // Phénomène : Perot (19% des voix) fragmente le vote républicain-modéré
  // → Clinton l'emporte avec seulement 43%. Effet spoiler classique.
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

  // ── Historical: Allemagne 2021 ────────────────────────────────────────────
  // Phénomène : 6 partis, aucun > 30% → coalition obligatoire.
  // Les méthodes consensuelles (Borda, Schulze) avantagent les centristes.
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

  // ── Théorique: Cycle de Condorcet ────────────────────────────────────────
  // Phénomène : A bat B, B bat C, C bat A en duels directs →
  // aucun vainqueur Condorcet, les méthodes "cassent" le cycle différemment.
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

  // ── Théorique: Consensus parfait ────────────────────────────────────────
  // Phénomène : Le candidat du centre gagne sous toutes les méthodes.
  // Référence "idéale" pour comparer avec des cas problématiques.
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

  // ── Existing preserved scenarios ──────────────────────────────────────────
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

// ── Scenario meta (cleared on manual config change) ───────────────────────────

export interface ScenarioMeta {
  id:          string;
  name:        string;
  description: string;
  phenomenon:  string;
}

// ── Context value ─────────────────────────────────────────────────────────────

interface ElectionContextValue {
  config:            ElectionConfig;
  setConfig:         (patch: Partial<ElectionConfig>) => void;
  setConfigDeep:     (path: string, value: unknown) => void;
  /** Full overwrite — used by scenario import to restore a saved config. */
  replaceConfig:     (next: ElectionConfig) => void;
  resetConfig:       () => void;
  applyScenario:     (name: string) => void;
  scenarioNames:     string[];
  scenarioMeta:      ScenarioMeta | null;
  clearScenarioMeta: () => void;
}

const ElectionContext = createContext<ElectionContextValue>({
  config:            DEFAULT_CONFIG,
  setConfig:         () => {},
  setConfigDeep:     () => {},
  replaceConfig:     () => {},
  resetConfig:       () => {},
  applyScenario:     () => {},
  scenarioNames:     Object.keys(SCENARIOS),
  scenarioMeta:      null,
  clearScenarioMeta: () => {},
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

  const [scenarioMeta, setScenarioMeta] = useState<ScenarioMeta | null>(null);

  useEffect(() => {
    try { localStorage.setItem(LS_KEY, JSON.stringify(config)); } catch {}
  }, [config]);

  const setConfig = useCallback((patch: Partial<ElectionConfig>) => {
    setConfigState((prev) => ({ ...prev, ...patch }));
    // Manual changes clear the active scenario badge
    setScenarioMeta(null);
  }, []);

  const setConfigDeep = useCallback((path: string, value: unknown) => {
    setConfigState((prev) => deepSet(prev, path, value) as ElectionConfig);
    setScenarioMeta(null);
  }, []);

  const replaceConfig = useCallback((next: ElectionConfig) => {
    setConfigState(next);
    setScenarioMeta(null);
  }, []);

  const resetConfig = useCallback(() => {
    setConfigState(DEFAULT_CONFIG);
    setScenarioMeta(null);
  }, []);

  const applyScenario = useCallback((name: string) => {
    const scenario = SCENARIOS[name];
    if (!scenario) return;
    setConfigState(scenario);
    setScenarioMeta(
      scenario.description
        ? {
            id:          name,
            name,
            description: scenario.description,
            phenomenon:  scenario.phenomenon ?? '',
          }
        : null
    );
  }, []);

  const clearScenarioMeta = useCallback(() => setScenarioMeta(null), []);

  return (
    <ElectionContext.Provider value={{
      config, setConfig, setConfigDeep, replaceConfig, resetConfig,
      applyScenario, scenarioNames: Object.keys(SCENARIOS),
      scenarioMeta, clearScenarioMeta,
    }}>
      {children}
    </ElectionContext.Provider>
  );
};
