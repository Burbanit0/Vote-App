import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useElection, usePlayground } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';
import { useMetaTags } from '../hooks/useMetaTags';
import { runProfileSimulate, type ProfileSimulateResult } from '../services/profileApi';
import LeaderCanvas from '../components/playground/LeaderCanvas';
import ParliamentCanvas from '../components/playground/ParliamentCanvas';
import FlipReveal from '../components/playground/FlipReveal';
import { sampleVoters, type Rule } from '../lib/playgroundVoting';
import {
  driftCandidates,
  medianPoint,
  shakeWinRates,
  type ShakeResult,
} from '../lib/playgroundDynamics';
import {
  runAssembly,
  runAssemblyScorecard,
  type AssemblyResult,
  type AssemblyScorecardResult,
} from '../services/assemblyApi';
import Scorecard, { type ScorecardAxis } from '../components/playground/Scorecard';
import ValuesPanel from '../components/playground/ValuesPanel';
import {
  leaderScorecard,
  LEADER_AXES_KEYS,
  LEADER_RULES,
  type LeaderScorecard,
  type LensItem,
} from '../lib/scorecard';

// Lab reshape — Phase P0: the two-mode playground shell. Two questions over ONE
// shared electorate: "Élire un dirigeant" (single office) vs "Composer un parlement"
// (party assembly). The canvas + scorecard are mode-driven placeholders here; the
// live dynamic visualizations land in P2/P3. Nothing is hidden — every assumption is
// a knob in the Setup rail. The existing 40 Lab tabs are untouched (additive).

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    num_voters: config.num_voters,
    seed: config.seed,
    candidates: config.candidates.map((c) => [c.name, c.x, c.y]),
  };
}

// ── Scorecard axes (P5): labels + stated conventions, by mode ────────────────

const LEADER_AXIS_META: { key: string; label: string; hint: string }[] = [
  { key: 'condorcet_efficiency', label: 'Efficacité Condorcet',
    hint: "Part des ré-échantillonnages (avec vainqueur de Condorcet) où la règle l'élit." },
  { key: 'strategic_resistance', label: 'Résistance stratégique',
    hint: 'Le vainqueur survit-il à une compression stratégique vers les deux favoris ? (heuristique documentée)' },
  { key: 'welfare', label: 'Bien-être (regret)',
    hint: '1 − regret bayésien normalisé du vainqueur (utilité = −distance).' },
  { key: 'majority_satisfaction', label: 'Satisfaction majoritaire',
    hint: 'Part des électeurs pour qui le vainqueur vaut au moins leur candidat médian.' },
  { key: 'simplicity', label: 'Simplicité',
    hint: 'Convention déclarée : complexité du bulletin et du dépouillement (sans bande).' },
  { key: 'stability', label: 'Stabilité',
    hint: 'Part des ré-échantillonnages élisant le vainqueur modal.' },
];

const PARLIAMENT_AXIS_META: { key: string; label: string; hint: string }[] = [
  { key: 'proportionality', label: 'Proportionnalité',
    hint: '1 − indice de Gallagher (normalisé).' },
  { key: 'pluralism', label: 'Pluralisme (diversité)',
    hint: 'Part de la diversité des voix (NEP) qui survit en sièges.' },
  { key: 'effective_votes', label: 'Voix utiles',
    hint: '1 − part des voix gaspillées.' },
  { key: 'minority_representation', label: 'Représentation des minorités',
    hint: 'Partis ≥ 3 % des voix détenant au moins un siège.' },
  { key: 'governability', label: 'Gouvernabilité',
    hint: '1 / taille de la plus petite coalition majoritaire.' },
  { key: 'gerrymander_resistance', label: 'Résistance au charcutage',
    hint: 'Stabilité des sièges quand la carte des circonscriptions change (re-découpage x→y).' },
];

const PARLIAMENT_AXES_KEYS = PARLIAMENT_AXIS_META.map((a) => a.key);
const STRUCTURE_LABELS: Record<string, string> = {
  pr: 'Proportionnelle (listes)',
  fptp: 'Circonscriptions (FPTP)',
  mmp: 'Mixte (MMP)',
};
const RULE_LABELS_LENS: Record<string, string> = {
  plurality: 'Pluralité (1 tour)',
  two_round: 'Deux tours',
  irv: 'Vote alternatif (IRV)',
  borda: 'Borda',
  approval: 'Approbation',
  condorcet: 'Condorcet (Copeland)',
};

const defaultWeights = (keys: readonly string[]): Record<string, number> =>
  Object.fromEntries(keys.map((k) => [k, 0.5]));

// ── Page ────────────────────────────────────────────────────────────────────

const PlaygroundPage: React.FC = () => {
  useMetaTags({
    title: 'Playground — Élire un dirigeant ou composer un parlement',
    description:
      'Un même électorat, deux questions : élire un dirigeant ou composer un parlement. Configurez chaque hypothèse et observez le caractère politique s’inverser.',
  });

  const { config, setConfig } = useElection();
  const { playground, setMode, setPlayground, setPlaygroundDeep, applyPreset, presets } =
    usePlayground();
  const { mode, space, behavior, prefSource, assembly } = playground;
  const pointWord = mode === 'leader' ? 'candidats' : 'partis';
  const { result, loading } = useProfileDiagnostics(config, playground);
  const { assembly: assemblyResult, loading: assemblyLoading } = useAssembly(
    config,
    playground,
    mode === 'parliament'
  );

  // Single-office canvas (P2): a deterministic voter cloud + draggable candidates.
  const [leaderRule, setLeaderRule] = React.useState<Rule>('plurality');
  const voters = React.useMemo(
    () => sampleVoters(config.num_voters, config.seed, config.ideology),
    [config.num_voters, config.seed, config.ideology]
  );
  const moveCandidate = React.useCallback(
    (index: number, x: number, y: number) => {
      setConfig({
        candidates: config.candidates.map((c, i) => (i === index ? { ...c, x, y } : c)),
      });
    },
    [config.candidates, setConfig]
  );

  // ── Dynamic layer (P4) ────────────────────────────────────────────────────
  // Campaign time scrubber: vote-seeking drift toward the median voter.
  const [campaignT, setCampaignT] = React.useState(0);
  const [playing, setPlaying] = React.useState(false);
  const median = React.useMemo(() => medianPoint(voters), [voters]);
  const displayedCandidates = React.useMemo(
    () => (campaignT > 0 ? driftCandidates(config.candidates, median, campaignT) : config.candidates),
    [config.candidates, median, campaignT]
  );
  React.useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setCampaignT((t) => {
        if (t >= 1) {
          setPlaying(false);
          return 1;
        }
        return Math.min(1, t + 0.02);
      });
    }, 80);
    return () => clearInterval(id);
  }, [playing]);
  // Dragging edits the configured (J0) positions — disable while scrubbed.
  const moveDisplayed = campaignT > 0 ? () => {} : moveCandidate;

  // "Shake the assumptions": re-roll the electorate, win-rate per candidate.
  const [shakeOn, setShakeOn] = React.useState(false);
  const [shake, setShake] = React.useState<ShakeResult | null>(null);
  const shakeKey = JSON.stringify({
    on: shakeOn,
    rule: leaderRule,
    cands: displayedCandidates.map((c) => [c.name, c.x, c.y]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
  });
  React.useEffect(() => {
    if (!shakeOn) {
      setShake(null);
      return;
    }
    const t = setTimeout(() => {
      setShake(
        shakeWinRates(
          displayedCandidates,
          leaderRule,
          Math.min(config.num_voters, 300),
          config.seed,
          config.ideology
        )
      );
    }, 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shakeKey]);

  // ── Scorecard + values lens (P5) ──────────────────────────────────────────
  const [leaderSc, setLeaderSc] = React.useState<LeaderScorecard | null>(null);
  const leaderScKey = JSON.stringify({
    on: mode === 'leader',
    cands: config.candidates.map((c) => [c.name, c.x, c.y]),
    n: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
  });
  React.useEffect(() => {
    if (mode !== 'leader') return;
    const t = setTimeout(() => {
      setLeaderSc(
        leaderScorecard(
          config.candidates,
          Math.min(config.num_voters, 200),
          config.seed,
          config.ideology,
          20
        )
      );
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parlScKey]);

  const [leaderWeights, setLeaderWeights] = React.useState(() => defaultWeights(LEADER_AXES_KEYS));
  const [parlWeights, setParlWeights] = React.useState(() => defaultWeights(PARLIAMENT_AXES_KEYS));

  const axisMeta = mode === 'leader' ? LEADER_AXIS_META : PARLIAMENT_AXIS_META;
  const currentAxes: ScorecardAxis[] = axisMeta.map(({ key, label, hint }) => ({
    key,
    label,
    hint,
    band:
      mode === 'leader'
        ? leaderSc?.[leaderRule]?.[key] ?? null
        : parlSc?.structures?.[assembly.structure]?.[key] ?? null,
  }));
  const lensItems: LensItem[] =
    mode === 'leader'
      ? leaderSc
        ? LEADER_RULES.map((r) => ({ id: r, axes: leaderSc[r] }))
        : []
      : parlSc
        ? Object.keys(STRUCTURE_LABELS).map((s) => ({ id: s, axes: parlSc.structures[s] }))
        : [];

  return (
    <div data-testid="playground-page" className="container mx-auto px-3 py-4">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">🎛 Playground</h1>
        <p className="text-sm text-muted-foreground">
          Un même électorat, deux questions. Basculez entre les deux et observez le caractère
          politique s’inverser — rien n’est caché, chaque hypothèse est un réglage.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[20rem_1fr_18rem]">
        {/* ── Setup rail ── */}
        <Card className="h-fit">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 p-4 pt-2">
            {/* Mode toggle */}
            <div className="grid grid-cols-2 gap-2">
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
                🏛 Parlement
              </Button>
            </div>

            {/* Presets */}
            <Field label="Point de départ (synthétique)">
              <div className="flex flex-col gap-1.5">
                {presets.map((p) => (
                  <button
                    key={p.id}
                    data-testid={`preset-${p.id}`}
                    type="button"
                    onClick={() => applyPreset(p.id)}
                    className={cn(
                      'rounded-md border border-border px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground'
                    )}
                    title={p.description}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </Field>

            {/* Electorate summary */}
            <div className="rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
              {config.candidates.length} {pointWord} · {config.num_voters} électeurs ·{' '}
              {config.ideology}
            </div>

            {/* Paradox/cycle rate read-out (P1) */}
            <div
              data-testid="cycle-rate"
              className="rounded-md border border-border px-2.5 py-2"
              title="Part des électorats ré-échantillonnés sans vainqueur de Condorcet — un taux élevé signale que le résultat dépend fortement des hypothèses."
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  Taux de paradoxe (cycles)
                </span>
                <span className="text-sm font-semibold tabular-nums">
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

            {/* Knobs */}
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
                onChange={(e) =>
                  setPlayground({ prefSource: e.target.value as typeof prefSource })
                }
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

            {/* Assembly knobs — only relevant in parliament mode */}
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
                    onChange={(e) =>
                      setPlaygroundDeep('assembly.structure', e.target.value)
                    }
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
                <Field
                  label={`Seuil : ${Math.round(assembly.threshold * 100)} %`}
                  htmlFor="pg-threshold"
                >
                  <input
                    id="pg-threshold"
                    type="range"
                    min={0}
                    max={0.15}
                    step={0.01}
                    value={assembly.threshold}
                    onChange={(e) =>
                      setPlaygroundDeep('assembly.threshold', Number(e.target.value))
                    }
                  />
                </Field>
                <Field label="Répartition des sièges" htmlFor="pg-appt">
                  <select
                    id="pg-appt"
                    className={selectCls}
                    value={assembly.apportionment}
                    onChange={(e) =>
                      setPlaygroundDeep('assembly.apportionment', e.target.value)
                    }
                  >
                    <option value="dhondt">D’Hondt</option>
                    <option value="sainte_lague">Sainte-Laguë</option>
                  </select>
                </Field>
                <label
                  className="flex items-center gap-2 text-sm"
                  title="Les électeurs désertent les partis non viables (FPTP : hors du top-2 de leur circonscription ; proportionnelle : sous le seuil) pour leur parti viable le plus proche — la loi de Duverger en mécanique."
                >
                  <input
                    data-testid="duverger-toggle"
                    type="checkbox"
                    checked={assembly.strategic_desertion}
                    onChange={(e) =>
                      setPlaygroundDeep('assembly.strategic_desertion', e.target.checked)
                    }
                  />
                  Désertion stratégique (Duverger)
                </label>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Canvas slot ── */}
        <Card>
          <CardContent className="p-3">
            {/* The flip centerpiece (P4): same electorate, the question flips. */}
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">
                {mode === 'leader' ? '👑 Élire un dirigeant' : '🏛 Composer un parlement'}
              </span>
              <Button
                data-testid="flip-button"
                variant="outline"
                size="sm"
                onClick={() => setMode(mode === 'leader' ? 'parliament' : 'leader')}
              >
                ↔ Basculer la question
              </Button>
            </div>
            <FlipReveal modeKey={mode} caption="Mêmes électeurs, caractère opposé.">
              {mode === 'leader' ? (
                <div className="flex flex-col gap-3">
                  <LeaderCanvas
                    candidates={displayedCandidates}
                    voters={voters}
                    rule={leaderRule}
                    onRuleChange={setLeaderRule}
                    onMoveCandidate={moveDisplayed}
                  />

                  {/* Time scrubber (P4): campaign drift toward the median voter. */}
                  <div data-testid="campaign-scrubber" className="flex items-center gap-2 text-sm">
                    <Button
                      data-testid="campaign-play"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (!playing && campaignT >= 1) setCampaignT(0);
                        setPlaying((p) => !p);
                      }}
                    >
                      {playing ? '⏸' : '▶'}
                    </Button>
                    <span className="w-28 shrink-0 tabular-nums text-muted-foreground">
                      Campagne — J{Math.round(campaignT * 30)}
                    </span>
                    <input
                      data-testid="campaign-slider"
                      type="range"
                      className="flex-1"
                      min={0}
                      max={1}
                      step={0.02}
                      value={campaignT}
                      onChange={(e) => {
                        setPlaying(false);
                        setCampaignT(Number(e.target.value));
                      }}
                      title="Modèle affiché : les candidats en quête de voix dérivent vers l'électeur médian (Hotelling–Downs)."
                    />
                    {campaignT > 0 && (
                      <span className="text-xs text-muted-foreground/70">
                        (revenez à J0 pour déplacer les candidats)
                      </span>
                    )}
                  </div>

                  {/* Shake the assumptions (P4): re-roll the electorate → win-rate bands. */}
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
                    {shakeOn && shake && (
                      <div data-testid="shake-bands" className="flex flex-col gap-1">
                        <p className="text-sm">
                          {shake.top ? (
                            <>
                              <strong>{shake.top}</strong> tient{' '}
                              <strong>{Math.round((shake.rates[shake.top] ?? 0) * 100)} %</strong>{' '}
                              des {shake.replications} ré-échantillonnages.
                            </>
                          ) : (
                            '—'
                          )}
                        </p>
                        {displayedCandidates.map((c) => (
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
                            <span className="w-10 text-right tabular-nums text-muted-foreground">
                              {Math.round((shake.rates[c.name] ?? 0) * 100)} %
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <ParliamentCanvas
                  parties={config.candidates}
                  voters={voters}
                  result={assemblyResult}
                  loading={assemblyLoading}
                  onMoveParty={moveCandidate}
                />
              )}
            </FlipReveal>
          </CardContent>
        </Card>

        {/* ── Scorecard + values lens (P5) ── */}
        <Card className="h-fit">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-base">
              Bilan —{' '}
              {mode === 'leader'
                ? RULE_LABELS_LENS[leaderRule]
                : STRUCTURE_LABELS[assembly.structure]}
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
            <ValuesPanel
              items={lensItems}
              axisKeys={mode === 'leader' ? [...LEADER_AXES_KEYS] : PARLIAMENT_AXES_KEYS}
              axisLabels={Object.fromEntries(axisMeta.map((a) => [a.key, a.label]))}
              itemLabels={mode === 'leader' ? RULE_LABELS_LENS : STRUCTURE_LABELS}
              weights={mode === 'leader' ? leaderWeights : parlWeights}
              onWeightChange={(k, v) =>
                mode === 'leader'
                  ? setLeaderWeights((w) => ({ ...w, [k]: v }))
                  : setParlWeights((w) => ({ ...w, [k]: v }))
              }
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PlaygroundPage;
