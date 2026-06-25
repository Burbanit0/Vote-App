import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useElection, usePlayground } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';
import { useMetaTags } from '../hooks/useMetaTags';
import { runProfileSimulate, type ProfileSimulateResult } from '../services/profileApi';
import LeaderCanvas, { type Lens } from '../components/playground/LeaderCanvas';
import ParliamentCanvas from '../components/playground/ParliamentCanvas';
import FlipReveal from '../components/playground/FlipReveal';
import MomentRail, { MOMENTS, type MomentId } from '../components/playground/MomentRail';
import CampaignTimeline from '../components/campaign/CampaignTimeline';
import {
  sampleVoters,
  applyTurnout,
  RULE_LABELS,
  type Rule,
  type Pt,
} from '../lib/playgroundVoting';
import { shakeWinRates, type ShakeResult } from '../lib/playgroundDynamics';
import {
  runAssembly,
  runAssemblyScorecard,
  type AssemblyResult,
  type AssemblyScorecardResult,
} from '../services/assemblyApi';
import Scorecard, { type ScorecardAxis } from '../components/playground/Scorecard';
import MethodInfo from '../components/playground/MethodInfo';
import ScenarioInfo from '../components/playground/ScenarioInfo';
import ValuesPanel from '../components/playground/ValuesPanel';
import {
  leaderScorecard,
  consensusIndex,
  dialWeights,
  manipulationProbe,
  MANIP_COMPLEXITY,
  LEADER_AXES_KEYS,
  LEADER_RULES,
  type LeaderScorecard,
  type LensItem,
} from '../lib/scorecard';
import DemocracyMap from '../components/playground/DemocracyMap';
import IssuesPanel from '../components/playground/IssuesPanel';
import StructuralPanel from '../components/playground/StructuralPanel';
import Collapsible from '../components/playground/Collapsible';
import StrategicModule from '../components/playground/StrategicModule';
import SincerityModule from '../components/playground/SincerityModule';
import ElectorateComposer from '../components/playground/ElectorateComposer';
import { composeElectorate, COMMUNITY_PALETTE } from '../lib/playgroundElectorate';

// Contextual anchors — Lab phenomena re-homed next to the concept they deepen.
// Lazy + Collapsible-gated, so they add no compute until opened (perf invariant).
const MechanismsAnchor = React.lazy(
  () => import('../components/playground/anchors/MechanismsAnchor')
);
const AnalysisAnchor = React.lazy(() => import('../components/playground/anchors/AnalysisAnchor'));
const TheoryAnchor = React.lazy(() => import('../components/playground/anchors/TheoryAnchor'));
const SystemsAnchor = React.lazy(() => import('../components/playground/anchors/SystemsAnchor'));
const ResultsAnchor = React.lazy(() => import('../components/playground/anchors/ResultsAnchor'));
const AbstentionPanel = React.lazy(() => import('../components/shared/AbstentionPanel'));
const BlankVoteDivergencePanel = React.lazy(
  () => import('../components/shared/BlankVoteDivergencePanel')
);

const AnchorFallback: React.FC = () => (
  <p className="p-2 text-xs text-muted-foreground">Chargement…</p>
);

// Single-instrument shell. One page, one live instrument. A persistent
// Dirigeant/Assemblée toggle (the duality) sits orthogonally above a rail of four
// "moments" (Électorat → Méthode → Stratégie → Campagne), simple to complex, one
// active at a time. The active moment swaps the LEFT control panel and drives the
// instrument's lens; the central map + readouts stay live throughout. Nothing is
// hidden in a drawer — the other moments' effects are already in the picture.

// ── Small field primitives (native, Tailwind-styled) ────────────────────────

const Field: React.FC<{ label: string; htmlFor?: string; children: React.ReactNode }> = ({
  label,
  htmlFor,
  children,
}) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
      {label}
    </label>
    {children}
  </div>
);

const selectCls =
  'w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

// ── Live profile diagnostics (P1) ───────────────────────────────────────────
// Debounced call to the profile engine on every assumption change, surfacing the
// paradox/cycle rate. The number visibly moves as the source/dims change — the
// meta-lesson that conclusions are conditional on the model.
function useProfileDiagnostics(
  config: ElectionConfig,
  playground: PlaygroundState
): { result: ProfileSimulateResult | null; loading: boolean } {
  const [result, setResult] = React.useState<ProfileSimulateResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const key = JSON.stringify(toProfileKey(config, playground));

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    const t = setTimeout(() => {
      runProfileSimulate(config, playground)
        .then((r) => {
          if (alive) setResult(r);
        })
        .catch(() => {
          if (alive) setResult(null);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 350);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [key]);

  return { result, loading };
}

// Debounced call to /assembly (P3) — only while in parliament mode.
function useAssembly(
  config: ElectionConfig,
  playground: PlaygroundState,
  enabled: boolean
): { assembly: AssemblyResult | null; loading: boolean } {
  const [assembly, setAssembly] = React.useState<AssemblyResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const key = JSON.stringify({
    enabled,
    a: playground.assembly,
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    parties: config.candidates.map((c) => [c.name, c.x, c.y]),
  });

  React.useEffect(() => {
    if (!enabled) return;
    let alive = true;
    setLoading(true);
    const t = setTimeout(() => {
      runAssembly(config, playground)
        .then((r) => {
          if (alive) setAssembly(r);
        })
        .catch(() => {
          if (alive) setAssembly(null);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 300);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [key]);

  return { assembly, loading };
}

// The minimal set of fields that change the profile (avoids re-fetch on unrelated state).
function toProfileKey(config: ElectionConfig, pg: PlaygroundState) {
  return {
    source: pg.prefSource,
    dims: pg.space.dims,
    valence: pg.space.valenceEnabled,
    behavior: pg.behavior,
    prefParams: pg.prefParams,
    ballot: pg.ballot,
    num_voters: config.num_voters,
    seed: config.seed,
    candidates: config.candidates.map((c) => [c.name, c.x, c.y]),
  };
}

const BALLOT_LABELS: Record<string, string> = {
  full: 'Information complète',
  choose_one: 'Choix unique (1 croix)',
  approve: 'Approbation',
  rank_full: 'Classement complet',
  rank_truncated: 'Classement tronqué (top-k)',
  score: 'Notes (échelle)',
  grade: 'Mentions (JM)',
  cumulative: 'Cumulatif (budget de points)',
};

// ── Scorecard axes (P5): labels + stated conventions, by mode ────────────────

const LEADER_AXIS_META: { key: string; label: string; hint: string }[] = [
  {
    key: 'condorcet_efficiency',
    label: 'Efficacité Condorcet',
    hint: "Part des ré-échantillonnages (avec vainqueur de Condorcet) où la règle l'élit.",
  },
  {
    key: 'strategic_resistance',
    label: 'Résistance stratégique',
    hint: 'Le vainqueur survit-il à une compression stratégique vers les deux favoris ? (heuristique documentée)',
  },
  {
    key: 'welfare',
    label: 'Bien-être (regret)',
    hint: '1 − regret bayésien normalisé du vainqueur (utilité = −distance).',
  },
  {
    key: 'majority_satisfaction',
    label: 'Satisfaction majoritaire',
    hint: 'Part des électeurs pour qui le vainqueur vaut au moins leur candidat médian.',
  },
  {
    key: 'simplicity',
    label: 'Simplicité',
    hint: 'Convention déclarée : complexité du bulletin et du dépouillement (sans bande).',
  },
  {
    key: 'stability',
    label: 'Stabilité',
    hint: 'Part des ré-échantillonnages élisant le vainqueur modal.',
  },
];

const PARLIAMENT_AXIS_META: { key: string; label: string; hint: string }[] = [
  {
    key: 'proportionality',
    label: 'Proportionnalité',
    hint: '1 − indice de Gallagher (normalisé).',
  },
  {
    key: 'pluralism',
    label: 'Pluralisme (diversité)',
    hint: 'Part de la diversité des voix (NEP) qui survit en sièges.',
  },
  {
    key: 'effective_votes',
    label: 'Voix utiles',
    hint: '1 − part des voix gaspillées.',
  },
  {
    key: 'minority_representation',
    label: 'Représentation des minorités',
    hint: 'Partis ≥ 3 % des voix détenant au moins un siège.',
  },
  {
    key: 'governability',
    label: 'Gouvernabilité',
    hint: '1 / taille de la plus petite coalition majoritaire.',
  },
  {
    key: 'gerrymander_resistance',
    label: 'Résistance au charcutage',
    hint: 'Stabilité des sièges quand la carte des circonscriptions change (re-découpage x→y).',
  },
];

const PARLIAMENT_AXES_KEYS = PARLIAMENT_AXIS_META.map((a) => a.key);
const STRUCTURE_LABELS: Record<string, string> = {
  pr: 'Proportionnelle (listes)',
  fptp: 'Circonscriptions (FPTP)',
  mmp: 'Mixte (MMP)',
};
// The 15 leader rules' labels come from the voting lib (RULE_LABELS) so the
// selector, scorecard title and values lens stay in sync.
const defaultWeights = (keys: readonly string[]): Record<string, number> =>
  Object.fromEntries(keys.map((k) => [k, 0.5]));

// ── Page ────────────────────────────────────────────────────────────────────

const PlaygroundPage: React.FC = () => {
  useMetaTags({
    title: 'Playground — un instrument, du simple au complexe',
    description:
      'Un même électorat, un seul instrument. Choisissez la question (dirigeant ou assemblée), puis avancez moment par moment : électorat, méthode, stratégie, campagne — et observez les effets en direct.',
  });

  const { config, setConfig } = useElection();
  const { playground, setMode, setPlayground, setPlaygroundDeep, applyPreset, presets } =
    usePlayground();
  const { mode, space, behavior, prefSource, assembly, turnout } = playground;
  const pointWord = mode === 'leader' ? 'candidats' : 'partis';
  const { result, loading } = useProfileDiagnostics(config, playground);
  const { assembly: assemblyResult, loading: assemblyLoading } = useAssembly(
    config,
    playground,
    mode === 'parliament'
  );

  // The active "moment" — the station on the instrument's journey. Drives the
  // left control panel and the instrument's lens; the others stay one click away.
  const [activeMoment, setActiveMoment] = React.useState<MomentId>('electorate');
  const activeMomentMeta = MOMENTS.find((m) => m.id === activeMoment) ?? MOMENTS[0];

  // Single-office canvas (P2): a deterministic voter cloud + draggable candidates,
  // in the configured number of spatial dimensions (1/2/3).
  const dims = space.dims;
  const [leaderRule, setLeaderRule] = React.useState<Rule>('plurality');
  // Central-map lens: the moment sets a sensible default (Méthode → critères,
  // Stratégie → manipulation, sinon vainqueur). The user can still override it on
  // the instrument within the current moment.
  const [lens, setLens] = React.useState<Lens>('winner');
  React.useEffect(() => {
    setLens(
      activeMoment === 'method'
        ? 'criteria'
        : activeMoment === 'strategy'
          ? 'manipulation'
          : 'winner'
    );
  }, [activeMoment]);

  // Phase 0 perf: warm the heavy Recharts vendor chunk (its own split chunk) after
  // first paint, so the first behaviour/analysis panel that uses it opens without a
  // cold download+parse. Dynamic import keeps it a separate chunk; failure is ignored.
  React.useEffect(() => {
    let idle: number | undefined;
    let timer: number | undefined;
    const warm = () => {
      import('recharts').catch(() => {});
    };
    if (typeof window.requestIdleCallback === 'function') {
      idle = window.requestIdleCallback(warm);
    } else {
      timer = window.setTimeout(warm, 1500);
    }
    return () => {
      if (idle !== undefined && typeof window.cancelIdleCallback === 'function')
        window.cancelIdleCallback(idle);
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, []);
  // "You" — the sincere-vote voter, draggable on the map. Shown while the Stratégie
  // moment is active (the sincerity module lives there).
  const [youPos, setYouPos] = React.useState<Pt>({ x: -0.5, y: 0, z: 0 });
  const showYou = mode === 'leader' && activeMoment === 'strategy';
  // The composable electorate (engine): when 'composed', a community mixture
  // replaces the single ideology Gaussian and tags each voter with its bloc so
  // the leader views can colour the cloud. 'simple' keeps the prior behaviour.
  const electorate = playground.electorate;
  const composed = electorate.mode === 'composed';
  const electorateSampler = React.useMemo(
    () =>
      composed
        ? {
            communities: electorate.communities,
            correlation: electorate.correlation,
            noise: electorate.noise,
          }
        : null,
    [composed, electorate.communities, electorate.correlation, electorate.noise]
  );
  const voters = React.useMemo(() => {
    if (electorateSampler) {
      const { voters: vs, community } = composeElectorate(
        electorateSampler.communities,
        electorateSampler.correlation,
        config.num_voters,
        config.seed,
        dims,
        electorateSampler.noise
      );
      // Tag each voter with its bloc index (extra prop survives applyTurnout,
      // which preserves object identity) for downstream colouring.
      return vs.map((v, i) => ({ ...v, _community: community[i] }));
    }
    return sampleVoters(config.num_voters, config.seed, config.ideology, dims);
  }, [electorateSampler, config.num_voters, config.seed, config.ideology, dims]);
  const moveCandidate = React.useCallback(
    (index: number, x: number, y: number, z?: number) => {
      setConfig({
        candidates: config.candidates.map((c, i) =>
          i === index ? { ...c, x, y, ...(z !== undefined ? { z } : {}) } : c
        ),
      });
    },
    [config.candidates, setConfig]
  );

  // "Pin this drifted instant back as the new baseline electorate" — the one
  // explicit write-back from the campaign moment into the shared snapshot.
  const pinToPlayground = React.useCallback(
    (pinned: { name: string; x: number; y: number; z?: number }[]) =>
      setConfig({
        candidates: pinned.map((c) => ({ name: c.name, x: c.x, y: c.y, z: c.z })),
      }),
    [setConfig]
  );

  // ── Derived electorate ────────────────────────────────────────────────────
  // Project candidates onto the active dimension count so the math, the map and
  // the re-rolls all agree (1-D zeroes y,z; 2-D zeroes z; 3-D keeps all).
  const leaderCandidates = React.useMemo(
    () =>
      config.candidates.map((c) => ({
        ...c,
        y: dims >= 2 ? c.y : 0,
        z: dims >= 3 ? (c.z ?? 0) : 0,
      })),
    [config.candidates, dims]
  );
  // Differential turnout: the abstainers leave, reshaping the live electorate.
  const turnoutResult = React.useMemo(
    () => applyTurnout(voters, leaderCandidates, turnout.model, turnout.intensity),
    [voters, leaderCandidates, turnout.model, turnout.intensity]
  );
  const votingVoters = turnoutResult.voters;
  // Per-voter colour by community (composed electorate only) — aligned with the
  // post-turnout cloud since applyTurnout preserves the tagged objects.
  const voterColors = React.useMemo(
    () =>
      composed
        ? votingVoters.map(
            (v) =>
              COMMUNITY_PALETTE[
                ((v as { _community?: number })._community ?? 0) % COMMUNITY_PALETTE.length
              ]
          )
        : undefined,
    [composed, votingVoters]
  );

  // "Shake the assumptions": re-roll the electorate, win-rate per candidate.
  const [shakeOn, setShakeOn] = React.useState(false);
  const [shake, setShake] = React.useState<ShakeResult | null>(null);
  const shakeKey = JSON.stringify({
    on: shakeOn,
    rule: leaderRule,
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    dims,
    turnout,
    electorate: electorateSampler,
  });
  React.useEffect(() => {
    if (!shakeOn) {
      setShake(null);
      return;
    }
    const t = setTimeout(() => {
      setShake(
        shakeWinRates(
          leaderCandidates,
          leaderRule,
          Math.min(config.num_voters, 300),
          config.seed,
          config.ideology,
          60,
          dims,
          turnout,
          electorateSampler
        )
      );
    }, 200);
    return () => clearTimeout(t);
  }, [shakeKey]);

  // ── Scorecard + values lens (P5) ──────────────────────────────────────────
  const [leaderSc, setLeaderSc] = React.useState<LeaderScorecard | null>(null);
  const leaderScKey = JSON.stringify({
    on: mode === 'leader',
    cands: leaderCandidates.map((c) => [c.name, c.x, c.y, c.z]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    dims,
    turnout,
    electorate: electorateSampler,
  });
  React.useEffect(() => {
    if (mode !== 'leader') return;
    const t = setTimeout(() => {
      setLeaderSc(
        leaderScorecard(
          leaderCandidates,
          Math.min(config.num_voters, 200),
          config.seed,
          config.ideology,
          20,
          dims,
          turnout,
          electorateSampler
        )
      );
    }, 250);
    return () => clearTimeout(t);
  }, [leaderScKey]);

  const [parlSc, setParlSc] = React.useState<AssemblyScorecardResult | null>(null);
  const parlScKey = JSON.stringify({
    on: mode === 'parliament',
    parties: config.candidates.map((c) => [c.name, c.x, c.y]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
    seats: assembly.seats,
    threshold: assembly.threshold,
    appt: assembly.apportionment,
    des: assembly.strategic_desertion,
  });
  React.useEffect(() => {
    if (mode !== 'parliament') return;
    let alive = true;
    const t = setTimeout(() => {
      runAssemblyScorecard(config, playground)
        .then((r) => {
          if (alive) setParlSc(r);
        })
        .catch(() => {
          if (alive) setParlSc(null);
        });
    }, 350);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [parlScKey]);

  const [leaderWeights, setLeaderWeights] = React.useState(() => defaultWeights(LEADER_AXES_KEYS));
  const [parlWeights, setParlWeights] = React.useState(() => defaultWeights(PARLIAMENT_AXES_KEYS));

  // FA-2 — the Lijphart identity dial drives correlated weights; any granular
  // slider touch switches to manual mode (the stated escape hatch).
  const [lensMode, setLensMode] = React.useState<'dial' | 'granular'>('dial');
  const [dial, setDial] = React.useState(0.5);
  const manualWeights = mode === 'leader' ? leaderWeights : parlWeights;
  const effectiveWeights = lensMode === 'dial' ? dialWeights(dial, mode) : manualWeights;

  // Consensus index per structure (parliament mode) for the democracy map.
  const democracyEntries = React.useMemo(
    () =>
      parlSc
        ? Object.keys(STRUCTURE_LABELS).map((s) => ({
            structure: s,
            label: STRUCTURE_LABELS[s].split(' ')[0],
            index: consensusIndex(parlSc.structures[s]),
          }))
        : [],
    [parlSc]
  );

  // FC-1 — manipulation hardness: the empirical compromise probe on THIS
  // electorate for the selected rule, plus the plurality-vs-IRV worked example.
  const manipDetail = React.useMemo(() => {
    if (mode !== 'leader') return null;
    return {
      probe: manipulationProbe(votingVoters, leaderCandidates, leaderRule),
      easy: manipulationProbe(votingVoters, leaderCandidates, 'plurality'),
      hard: manipulationProbe(votingVoters, leaderCandidates, 'irv'),
    };
  }, [mode, votingVoters, leaderCandidates, leaderRule]);

  const axisMeta = mode === 'leader' ? LEADER_AXIS_META : PARLIAMENT_AXIS_META;
  const currentAxes: ScorecardAxis[] = axisMeta.map(({ key, label, hint }) => ({
    key,
    label,
    hint,
    band:
      mode === 'leader'
        ? (leaderSc?.[leaderRule]?.[key] ?? null)
        : (parlSc?.structures?.[assembly.structure]?.[key] ?? null),
  }));
  const lensItems: LensItem[] =
    mode === 'leader'
      ? leaderSc
        ? LEADER_RULES.map((r) => ({ id: r, axes: leaderSc[r] }))
        : []
      : parlSc
        ? Object.keys(STRUCTURE_LABELS).map((s) => ({ id: s, axes: parlSc.structures[s] }))
        : [];

  // ── Moment ① Électorat — who votes, how they cluster and behave ────────────
  const electorateControls = (
    <>
      <Collapsible
        title="🧭 Composer l’électorat"
        subtitle={
          composed ? `${electorate.communities.length} communautés · mélange` : 'gaussien simple'
        }
        testid="module-electorate"
      >
        <ElectorateComposer />
      </Collapsible>

      <Field label="Point de départ (synthétique)">
        <div className="flex flex-col gap-1.5">
          {presets.map((p) => (
            <div key={p.id} className="flex items-center gap-1">
              <button
                data-testid={`preset-${p.id}`}
                type="button"
                onClick={() => applyPreset(p.id)}
                className={cn(
                  'flex-1 rounded-md border border-border px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground'
                )}
                title={p.description}
              >
                {p.label}
              </button>
              <ScenarioInfo scenario={p.id} />
            </div>
          ))}
        </div>
      </Field>

      <div className="rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
        {config.candidates.length} {pointWord} · {config.num_voters} électeurs · {config.ideology}
      </div>

      <Field label="Dimensions de l’espace" htmlFor="pg-dims">
        <select
          id="pg-dims"
          className={selectCls}
          value={space.dims}
          onChange={(e) => setPlaygroundDeep('space.dims', Number(e.target.value))}
        >
          <option value={1}>1D — un seul axe</option>
          <option value={2}>2D — deux axes</option>
          <option value={3}>3D — trois axes</option>
        </select>
      </Field>

      <Field label="Source des préférences" htmlFor="pg-source">
        <select
          id="pg-source"
          className={selectCls}
          value={prefSource}
          onChange={(e) => setPlayground({ prefSource: e.target.value as typeof prefSource })}
        >
          <option value="spatial">Spatiale (carte)</option>
          <option value="impartial">Culture impartiale</option>
          <option value="mallows">Mallows</option>
          <option value="urn">Urne de Pólya</option>
          <option value="handcrafted">Matrice sur mesure</option>
        </select>
      </Field>

      <Field label="Comportement des électeurs" htmlFor="pg-behavior">
        <select
          id="pg-behavior"
          className={selectCls}
          value={behavior}
          onChange={(e) => setPlayground({ behavior: e.target.value as typeof behavior })}
        >
          <option value="sincere">Sincère</option>
          <option value="strategic">Stratégique</option>
          <option value="mixed">Mixte</option>
        </select>
      </Field>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={space.valenceEnabled}
          onChange={(e) => setPlaygroundDeep('space.valenceEnabled', e.target.checked)}
        />
        Valence (qualité hors-idéologie)
      </label>

      {/* ── Participation / abstention (réalisme électoral) ── */}
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Participation (abstention)
        </p>
        <Field label="Modèle d’abstention" htmlFor="pg-turnout">
          <select
            id="pg-turnout"
            data-testid="turnout-select"
            className={selectCls}
            value={turnout.model}
            onChange={(e) => setPlaygroundDeep('turnout.model', e.target.value)}
          >
            <option value="full">Participation totale</option>
            <option value="alienation">Aliénation (trop loin de tous)</option>
            <option value="indifference">Indifférence (départage trop serré)</option>
          </select>
        </Field>
        {turnout.model !== 'full' && (
          <>
            <Field
              label={`Intensité : ${Math.round(turnout.intensity * 100)} %`}
              htmlFor="pg-turnout-int"
            >
              <input
                id="pg-turnout-int"
                data-testid="turnout-intensity"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={turnout.intensity}
                onChange={(e) => setPlaygroundDeep('turnout.intensity', Number(e.target.value))}
              />
            </Field>
            {mode === 'leader' && (
              <p data-testid="turnout-rate" className="text-[0.7rem] text-muted-foreground">
                Taux de participation :{' '}
                <strong>
                  {Math.round((votingVoters.length / Math.max(1, voters.length)) * 100)} %
                </strong>{' '}
                ({voters.length - votingVoters.length} abstentions)
              </p>
            )}
          </>
        )}
        <p className="text-[0.65rem] text-muted-foreground/70">
          Abstention de Downs : aliénation (même le meilleur choix est trop loin) ou indifférence
          (pas d’écart net entre les deux premiers).
        </p>
        <Collapsible
          title="🔬 Abstention différentielle (analyse)"
          subtitle="distribution complète"
          testid="anchor-abstention"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <AbstentionPanel />
          </React.Suspense>
        </Collapsible>
      </div>
    </>
  );

  // ── Moment ② Méthode — what the ballot can say + how it is counted ─────────
  const methodControls = (
    <>
      <p className="text-xs text-muted-foreground">
        La <strong>règle</strong> de décompte et la <strong>vue</strong> se choisissent directement
        sur l’instrument →. Ici, réglez ce que l’électeur peut <em>exprimer</em>.
      </p>

      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Bulletin (expression)
        </p>
        <Field label="Type de bulletin" htmlFor="pg-ballot">
          <select
            id="pg-ballot"
            data-testid="ballot-select"
            className={selectCls}
            value={playground.ballot.type}
            onChange={(e) => setPlaygroundDeep('ballot.type', e.target.value)}
          >
            {Object.entries(BALLOT_LABELS).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        {playground.ballot.type === 'rank_truncated' && (
          <Field label={`Classer le top ${playground.ballot.truncate_at}`} htmlFor="pg-truncate">
            <input
              id="pg-truncate"
              data-testid="ballot-truncate"
              type="range"
              min={1}
              max={Math.max(1, config.candidates.length)}
              step={1}
              value={playground.ballot.truncate_at}
              onChange={(e) => setPlaygroundDeep('ballot.truncate_at', Number(e.target.value))}
            />
          </Field>
        )}
        {(playground.ballot.type === 'score' || playground.ballot.type === 'grade') && (
          <Field
            label={`Niveaux : ${playground.ballot.type === 'grade' ? 7 : playground.ballot.score_levels}`}
            htmlFor="pg-levels"
          >
            <input
              id="pg-levels"
              type="range"
              min={2}
              max={10}
              step={1}
              value={playground.ballot.score_levels}
              disabled={playground.ballot.type === 'grade'}
              onChange={(e) => setPlaygroundDeep('ballot.score_levels', Number(e.target.value))}
            />
          </Field>
        )}

        {result && (
          <div
            data-testid="ballot-preview"
            className="rounded bg-muted/40 px-2 py-1.5 text-[0.7rem] text-muted-foreground"
            title="Le bulletin tel que l'électeur n°1 le remplirait — ce que la règle voit vraiment."
          >
            {Object.entries(result.sample_ballot)
              .sort((a, b) => b[1] - a[1])
              .map(([n, v]) => `${n} ${v}`)
              .join(' · ')}
          </div>
        )}

        {result && (
          <div data-testid="ballot-tradeoff" className="flex flex-col gap-1">
            {(
              [
                ['Expressivité', result.ballot_expressiveness],
                ['Charge cognitive', result.ballot_cognitive_load],
              ] as const
            ).map(([label, v]) => (
              <div key={label} className="flex items-center gap-2 text-[0.7rem]">
                <span className="w-24 shrink-0 text-muted-foreground">{label}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded bg-muted/50">
                  <div
                    className="h-full rounded bg-primary/70"
                    style={{ width: `${v * 100}%`, transition: 'width 300ms ease' }}
                  />
                </div>
                <span className="w-8 text-right font-mono tabular-nums text-muted-foreground">
                  {Math.round(v * 100)}
                </span>
              </div>
            ))}
          </div>
        )}

        {result && result.winner_flips.length > 0 && (
          <p
            data-testid="ballot-flips"
            className="text-[0.7rem] font-medium text-amber-600 dark:text-amber-400"
          >
            ⚠ À règle égale, ce bulletin change le vainqueur pour {result.winner_flips.length}{' '}
            méthode
            {result.winner_flips.length > 1 ? 's' : ''} : {result.winner_flips.join(', ')}.
          </p>
        )}
        {result && result.incompatible_methods.length > 0 && (
          <p className="text-[0.65rem] text-muted-foreground/70">
            {result.incompatible_methods.length} méthodes exclues (l’information du bulletin ne
            permet pas de les dépouiller honnêtement).
          </p>
        )}
        <Collapsible
          title="🔬 Divergence du vote blanc (analyse)"
          subtitle="règle du blanc"
          testid="anchor-blank"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <BlankVoteDivergencePanel />
          </React.Suspense>
        </Collapsible>
      </div>

      {/* Assembly counting rules — the parliament question's "method". */}
      {mode === 'parliament' && (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Assemblée
          </p>
          <Field label="Structure" htmlFor="pg-structure">
            <select
              id="pg-structure"
              className={selectCls}
              value={assembly.structure}
              onChange={(e) => setPlaygroundDeep('assembly.structure', e.target.value)}
            >
              <option value="pr">Proportionnelle (listes)</option>
              <option value="fptp">Circonscriptions (FPTP)</option>
              <option value="mmp">Mixte (MMP)</option>
            </select>
          </Field>
          <Field label={`Sièges : ${assembly.seats}`} htmlFor="pg-seats">
            <input
              id="pg-seats"
              type="range"
              min={10}
              max={500}
              step={10}
              value={assembly.seats}
              onChange={(e) => setPlaygroundDeep('assembly.seats', Number(e.target.value))}
            />
          </Field>
          <Field label={`Seuil : ${Math.round(assembly.threshold * 100)} %`} htmlFor="pg-threshold">
            <input
              id="pg-threshold"
              type="range"
              min={0}
              max={0.15}
              step={0.01}
              value={assembly.threshold}
              onChange={(e) => setPlaygroundDeep('assembly.threshold', Number(e.target.value))}
            />
          </Field>
          <Field label="Répartition des sièges" htmlFor="pg-appt">
            <select
              id="pg-appt"
              className={selectCls}
              value={assembly.apportionment}
              onChange={(e) => setPlaygroundDeep('assembly.apportionment', e.target.value)}
            >
              <option value="dhondt">D’Hondt</option>
              <option value="sainte_lague">Sainte-Laguë</option>
            </select>
          </Field>
        </div>
      )}
    </>
  );

  // ── Moment ③ Stratégie — sincere vs tactical, blank vote, manipulation ─────
  const strategyControls = (
    <>
      {mode === 'leader' ? (
        <>
          <div className="flex flex-col gap-2 rounded-md border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              🗳️ Vote sincère ou vote utile ?
            </p>
            <p className="text-[0.7rem] text-muted-foreground/80">
              Votre conviction, méthode par méthode — glissez le losange « Vous » sur la carte.
            </p>
            <SincerityModule
              voters={votingVoters}
              candidates={leaderCandidates}
              dims={dims}
              you={youPos}
              onYouChange={setYouPos}
            />
          </div>

          <Collapsible
            title="⚡ Vulnérabilité stratégique (Gibbard–Satterthwaite)"
            subtitle="à la demande · lent"
            testid="module-strategic"
          >
            <StrategicModule config={config} playground={playground} />
          </Collapsible>

          {manipDetail && (
            <div
              data-testid="manip-hardness"
              className="rounded-md border border-border px-2.5 py-2 text-[0.7rem]"
            >
              <p className="font-semibold uppercase tracking-wide text-muted-foreground">
                Manipulation : principe vs pratique
              </p>
              <p className="mt-1">
                Jouable en principe (Gibbard–Satterthwaite) · calcul du bon mensonge :{' '}
                <strong
                  className={
                    MANIP_COMPLEXITY[leaderRule].hard
                      ? 'text-green-700 dark:text-green-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }
                >
                  {MANIP_COMPLEXITY[leaderRule].label}
                </strong>{' '}
                <span className="text-muted-foreground">({MANIP_COMPLEXITY[leaderRule].ref})</span>
              </p>
              <p className="mt-0.5 text-muted-foreground">
                Sonde sur cet électorat :{' '}
                {manipDetail.probe.minCoalitionShare !== null ? (
                  <>
                    une coalition de{' '}
                    <strong>{Math.round(manipDetail.probe.minCoalitionShare * 100)} %</strong>{' '}
                    suffit (compromission naïve)
                  </>
                ) : (
                  <>aucune compromission naïve ≤ 40 % ne renverse le vainqueur ici</>
                )}
                {manipDetail.probe.backfired &&
                  ' · des tentatives se retournent contre la coalition'}
                .
              </p>
              <p className="mt-0.5 text-muted-foreground/80">
                Exemple :{' '}
                {manipDetail.easy.minCoalitionShare !== null
                  ? `sous pluralité, ${Math.round(manipDetail.easy.minCoalitionShare * 100)} % suffisent`
                  : 'sous pluralité, la compromission échoue ici'}
                {' ; la même stratégie sous IRV '}
                {manipDetail.hard.minCoalitionShare !== null
                  ? `demande ${Math.round(manipDetail.hard.minCoalitionShare * 100)} %`
                  : 'échoue'}
                {manipDetail.hard.backfired ? ' (et peut se retourner contre elle)' : ''}.
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Stratégie d’assemblée
          </p>
          <label
            className="flex items-center gap-2 text-sm"
            title="Les électeurs désertent les partis non viables (FPTP : hors du top-2 de leur circonscription ; proportionnelle : sous le seuil) pour leur parti viable le plus proche — la loi de Duverger en mécanique."
          >
            <input
              data-testid="duverger-toggle"
              type="checkbox"
              checked={assembly.strategic_desertion}
              onChange={(e) => setPlaygroundDeep('assembly.strategic_desertion', e.target.checked)}
            />
            Désertion stratégique (Duverger)
          </label>
          <p className="text-[0.7rem] text-muted-foreground/80">
            La désertion comprime les partis non viables vers leur voisin viable : Duverger, en
            mécanique. L’effet se lit en direct sur la composition de l’assemblée →.
          </p>
        </div>
      )}
    </>
  );

  // ── The central instrument — the live map + its headline reading ───────────
  const instrument = (
    <Card>
      <CardContent className="p-3">
        <div
          data-testid="cycle-rate"
          className="mb-3 rounded-md border border-border px-2.5 py-2"
          title="Part des électorats ré-échantillonnés sans vainqueur de Condorcet — un taux élevé signale que le résultat dépend fortement des hypothèses."
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Taux de paradoxe (cycles)
            </span>
            <span className="font-mono text-sm font-semibold tabular-nums">
              {loading || !result ? '…' : `${Math.round(result.cycle_rate * 100)} %`}
            </span>
          </div>
          {result && (
            <p className="mt-1 text-[0.7rem] text-muted-foreground/80">
              {result.condorcet_winner
                ? `Vainqueur de Condorcet : ${result.condorcet_winner}`
                : 'Aucun vainqueur de Condorcet (cycle).'}
            </p>
          )}
        </div>

        <FlipReveal modeKey={mode} caption="Mêmes électeurs, caractère opposé.">
          {mode === 'leader' ? (
            <div className="flex flex-col gap-3">
              <LeaderCanvas
                candidates={leaderCandidates}
                voters={votingVoters}
                rule={leaderRule}
                dims={dims}
                voterColors={voterColors}
                youMarker={showYou ? youPos : null}
                lens={lens}
                onLensChange={setLens}
                onMoveYou={(x, y) => setYouPos((p) => ({ ...p, x, y }))}
                onRuleChange={setLeaderRule}
                onMoveCandidate={moveCandidate}
              />

              {composed && (
                <div
                  data-testid="electorate-legend"
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.7rem] text-muted-foreground"
                >
                  {electorate.communities.map((c, i) => (
                    <span key={c.id} className="inline-flex items-center gap-1">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                      />
                      {c.label}
                    </span>
                  ))}
                </div>
              )}

              {/* Shake the assumptions: re-roll the electorate → win-rate bands. */}
              <div className="flex flex-col gap-1.5">
                <Button
                  data-testid="shake-toggle"
                  variant={shakeOn ? 'primary' : 'outline'}
                  size="sm"
                  className="self-start"
                  onClick={() => setShakeOn((s) => !s)}
                  title="Ré-échantillonne l'électorat 60 fois (mêmes hypothèses, nouveaux tirages) — sépare une propriété structurelle d'un réglage choisi."
                >
                  🎲 Secouer les hypothèses
                </Button>
                {shakeOn && (
                  <span className="text-xs text-muted-foreground">
                    Monte-Carlo complet dans les Explorations avancées (Analyse)
                  </span>
                )}
                {shakeOn && shake && (
                  <div data-testid="shake-bands" className="flex flex-col gap-1">
                    <p className="text-sm">
                      {shake.top ? (
                        <>
                          <strong>{shake.top}</strong> tient{' '}
                          <strong>{Math.round((shake.rates[shake.top] ?? 0) * 100)} %</strong> des{' '}
                          {shake.replications} ré-échantillonnages.
                        </>
                      ) : (
                        '—'
                      )}
                    </p>
                    {config.candidates.map((c) => (
                      <div key={c.name} className="flex items-center gap-2 text-xs">
                        <span className="w-24 truncate text-muted-foreground">{c.name}</span>
                        <div className="h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                          <div
                            className="h-full animate-pulse rounded bg-primary/70"
                            style={{
                              width: `${(shake.rates[c.name] ?? 0) * 100}%`,
                              transition: 'width 400ms ease',
                            }}
                          />
                        </div>
                        <span className="w-10 text-right font-mono tabular-nums text-muted-foreground">
                          {Math.round((shake.rates[c.name] ?? 0) * 100)} %
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <ParliamentCanvas
                parties={config.candidates}
                voters={voters}
                result={assemblyResult}
                loading={assemblyLoading}
                nominalSeats={assembly.seats}
                onMoveParty={moveCandidate}
              />
              <Collapsible
                title="🗺 Carte des démocraties (Lijphart)"
                subtitle="majoritaire ↔ consensus"
                testid="module-democracy"
              >
                {democracyEntries.length > 0 ? (
                  <DemocracyMap entries={democracyEntries} current={assembly.structure} />
                ) : (
                  <p className="text-xs text-muted-foreground">Calcul en cours…</p>
                )}
              </Collapsible>
              <Collapsible title="🗳 Enjeux & groupage (Ostrogorski)" testid="module-issues">
                <IssuesPanel config={config} playground={playground} />
              </Collapsible>
              <Collapsible title="⚖ Équités structurelles" testid="module-structural">
                <StructuralPanel
                  config={config}
                  partyNames={config.candidates.map((c) => c.name)}
                  playground={playground}
                />
              </Collapsible>
            </div>
          )}
        </FlipReveal>
      </CardContent>
    </Card>
  );

  // ── The readouts — the current state's bilan (method/structure scorecard) ──
  const readouts = (
    <Card className="h-fit">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="flex items-center gap-1 text-base">
          <span>
            Bilan —{' '}
            {mode === 'leader' ? RULE_LABELS[leaderRule] : STRUCTURE_LABELS[assembly.structure]}
          </span>
          {mode === 'leader' ? (
            <MethodInfo
              method={leaderRule}
              context={{ condorcetExists: result?.condorcet_winner != null }}
              placement="bottom"
            />
          ) : (
            <MethodInfo method={assembly.structure} placement="bottom" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 p-4 pt-2">
        <Scorecard
          axes={currentAxes}
          bandNote={
            mode === 'leader'
              ? '20 ré-échantillonnages'
              : `${parlSc?.replications ?? 24} ré-échantillonnages`
          }
        />

        <hr className="border-border" />

        {/* FA-2 — the identity dial (one value, correlated weights) */}
        <div data-testid="lijphart-dial-block" className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold uppercase tracking-wide text-muted-foreground">
              Votre sensibilité
            </span>
            <button
              type="button"
              data-testid="lens-granular-toggle"
              className="text-[0.7rem] text-primary underline-offset-2 hover:underline"
              onClick={() => {
                if (lensMode === 'dial') {
                  const seeded = dialWeights(dial, mode);
                  if (mode === 'leader') setLeaderWeights(seeded);
                  else setParlWeights(seeded);
                  setLensMode('granular');
                } else {
                  setLensMode('dial');
                }
              }}
            >
              {lensMode === 'dial' ? 'Réglage fin…' : '← Cadran simple'}
            </button>
          </div>
          {lensMode === 'dial' && (
            <>
              <input
                data-testid="lijphart-dial"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={dial}
                onChange={(e) => setDial(Number(e.target.value))}
                title="Un seul cadran qui règle des pondérations corrélées (convention déclarée) — le réglage fin reste disponible."
              />
              <div className="flex justify-between text-[0.68rem] text-muted-foreground">
                <span>Majoritaire (décisif)</span>
                <span>Consensualiste (inclusif)</span>
              </div>
            </>
          )}
        </div>

        <ValuesPanel
          items={lensItems}
          axisKeys={mode === 'leader' ? [...LEADER_AXES_KEYS] : PARLIAMENT_AXES_KEYS}
          axisLabels={Object.fromEntries(axisMeta.map((a) => [a.key, a.label]))}
          itemLabels={mode === 'leader' ? RULE_LABELS : STRUCTURE_LABELS}
          weights={effectiveWeights}
          granular={lensMode === 'granular'}
          onWeightChange={(k, v) => {
            setLensMode('granular');
            if (mode === 'leader') setLeaderWeights((w) => ({ ...w, [k]: v }));
            else setParlWeights((w) => ({ ...w, [k]: v }));
          }}
        />
      </CardContent>
    </Card>
  );

  // ── Frontières — the deep, optional explorations (a moment further) ────────
  const frontieres = (
    <>
      {mode === 'leader' && (
        <div className="mt-4">
          <Collapsible
            title="⚙️ Autres procédures de décision"
            subtitle="11 mécanismes (jury, sortition, délégation…)"
            testid="anchor-mechanisms"
          >
            <React.Suspense fallback={<AnchorFallback />}>
              <MechanismsAnchor />
            </React.Suspense>
          </Collapsible>
        </div>
      )}
      {mode === 'parliament' && (
        <div className="mt-4">
          <Collapsible
            title="🔬 Systèmes & circonscriptions"
            subtitle="7 vues (coalitions, districts, gerrymander…)"
            testid="anchor-systems"
          >
            <React.Suspense fallback={<AnchorFallback />}>
              <SystemsAnchor />
            </React.Suspense>
          </Collapsible>
        </div>
      )}
      <div className="mt-4">
        <Collapsible
          title="📋 Résultats complets (dépouillement)"
          subtitle="toutes les méthodes · animation"
          testid="anchor-results"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <ResultsAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
      <div className="mt-4">
        <Collapsible
          title="🔬 Analyse approfondie du résultat courant"
          subtitle="distributions · regret · manipulabilité"
          testid="anchor-analysis"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <AnalysisAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
      <div className="mt-4">
        <Collapsible
          title="🔬 Théorie & paradoxes du choix social"
          subtitle="Sen · jugements · McKelvey · pouvoir · recul démocratique…"
          testid="anchor-theory"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <TheoryAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
    </>
  );

  return (
    <div data-testid="playground-page" className="container mx-auto px-3 py-4">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">🎛 Instrument de vote</h1>
          <p className="text-sm text-muted-foreground">
            Un seul appareil, du simple au complexe — choisissez la question, puis avancez moment
            par moment.
          </p>
        </div>
        <div
          data-testid="mode-toggle"
          role="radiogroup"
          aria-label="Question"
          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border bg-card p-1"
        >
          <Button
            data-testid="mode-toggle-leader"
            variant={mode === 'leader' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setMode('leader')}
          >
            👑 Dirigeant
          </Button>
          <Button
            data-testid="mode-toggle-parliament"
            variant={mode === 'parliament' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setMode('parliament')}
          >
            🏛 Assemblée
          </Button>
        </div>
      </header>

      <MomentRail active={activeMoment} onSelect={setActiveMoment} />
      <p className="mb-4 mt-1.5 px-1 text-sm text-muted-foreground">{activeMomentMeta.hint}</p>

      {activeMoment === 'campaign' ? (
        <Card data-testid="moment-campaign-panel">
          <CardContent className="p-3">
            {config.candidates.length > 0 ? (
              <CampaignTimeline config={config} playground={playground} onPin={pinToPlayground} />
            ) : (
              <p className="p-2 text-sm text-muted-foreground">
                Composez d’abord un électorat dans le moment ① Électorat.
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[22rem_1fr]">
          <Card className="h-fit" data-testid={`moment-${activeMoment}-panel`}>
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-base">
                {activeMomentMeta.icon} {activeMomentMeta.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 p-4 pt-2">
              {activeMoment === 'electorate' && electorateControls}
              {activeMoment === 'method' && methodControls}
              {activeMoment === 'strategy' && strategyControls}
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4">
            {instrument}
            {readouts}
          </div>
        </div>
      )}

      {frontieres}
    </div>
  );
};

export default PlaygroundPage;
