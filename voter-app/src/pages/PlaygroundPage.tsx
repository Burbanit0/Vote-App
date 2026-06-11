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
import { sampleVoters, type Rule } from '../lib/playgroundVoting';
import { runAssembly, type AssemblyResult } from '../services/assemblyApi';

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

// ── Scorecard placeholder (replaced by the live scorecard in P5) ─────────────

const LEADER_AXES = [
  'Efficacité Condorcet',
  'Résistance stratégique',
  'Bien-être (regret bayésien)',
  'Satisfaction majorité / minorité',
  'Simplicité',
  'Décisivité',
];
const PARLIAMENT_AXES = [
  'Proportionnalité (Gallagher)',
  'Fragmentation (NEP)',
  'Voix gaspillées',
  'Représentation des minorités',
  'Gouvernabilité / coalitions',
  'Vulnérabilité au charcutage',
];

const ScorecardPlaceholder: React.FC<{ mode: 'leader' | 'parliament' }> = ({ mode }) => {
  const axes = mode === 'leader' ? LEADER_AXES : PARLIAMENT_AXES;
  return (
    <ul data-testid={`scorecard-${mode}`} className="flex flex-col gap-2">
      {axes.map((axis) => (
        <li key={axis} className="flex items-center justify-between gap-2 text-sm">
          <span className="text-muted-foreground">{axis}</span>
          <span className="h-1.5 w-16 rounded-full bg-muted" aria-hidden />
        </li>
      ))}
    </ul>
  );
};

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
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Canvas slot ── */}
        <Card>
          <CardContent className="p-3">
            {mode === 'leader' ? (
              <LeaderCanvas
                candidates={config.candidates}
                voters={voters}
                rule={leaderRule}
                onRuleChange={setLeaderRule}
                onMoveCandidate={moveCandidate}
              />
            ) : (
              <ParliamentCanvas
                parties={config.candidates}
                voters={voters}
                result={assemblyResult}
                loading={assemblyLoading}
                onMoveParty={moveCandidate}
              />
            )}
          </CardContent>
        </Card>

        {/* ── Scorecard slot ── */}
        <Card className="h-fit">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-base">Bilan</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-2">
            <ScorecardPlaceholder mode={mode} />
            <p className="mt-3 text-xs text-muted-foreground/70">
              Bandes Monte-Carlo et arbitrage par valeurs à venir (phase P5).
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PlaygroundPage;
