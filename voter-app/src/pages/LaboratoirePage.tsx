import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import {
  Columns2,
  X,
  Users,
  Scale,
  Swords,
  Landmark,
  Activity,
  FlaskConical,
  Ban,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import { PlaygroundProvider } from '../components/playground/PlaygroundController';
import {
  ElectorateOverrideProvider,
  ELECTORATE_PRESETS,
  useElection,
  usePlayground,
  type ElectionConfig,
  type PlaygroundState,
} from '../stores/useElectionStore';
import { AnchorFallback } from '../components/playground/playgroundFields';
import { track } from '../lib/analytics';
import {
  LAB_FAMILIES,
  DEFAULT_EXPERIMENT,
  locateExperiment,
  type FamilyId,
  type Located,
} from '../components/lab/labCatalog';

// LaboratoirePage — the specimen bench. The old page stacked 4 groups × 11
// sections × ~5 sub-accordions next to a 22rem sticky sidebar: everything was
// somewhere, nothing was anywhere. The redesign is the playground's own grammar
// extended to a collection:
//
//   family rail  →  catalogue of fiches  →  ONE full-width
//   bench (l'établi), with "Comparer un électorat" splitting it into the SAME
//   fiche read on two electorates (the phenomenon held constant, the electorate
//   varied) — a real comparison, not two unrelated panels side by side.
//
// All content lives in labCatalog.tsx as data (57 fiches — the integrity test
// proves nothing was lost). The page only navigates: nothing mounts unpicked,
// chips warm their chunk on hover, and ?exp=/&vs= deep-link any bench state.

// The five families are a taxonomy (methods / rules / systems / dynamics /
// theory), not a sequence — so they get a category icon, never an ordinal. A
// "1 2 3 4 5" here would imply a progression the archive doesn't have.
const FAMILY_ICON: Record<FamilyId, LucideIcon> = {
  methods: Scale,
  rules: Swords,
  systems: Landmark,
  dynamics: Activity,
  theory: FlaskConical,
  blank: Ban,
};

// Registration ticks — the instrument's corner marks, so a fiche reads as a
// specimen on the lab bench (echoes the Playground's scope frame).
const Corners: React.FC = () => (
  <>
    <span
      aria-hidden
      className="pointer-events-none absolute left-1.5 top-1.5 h-2.5 w-2.5 border-l border-t border-primary/55"
    />
    <span
      aria-hidden
      className="pointer-events-none absolute right-1.5 top-1.5 h-2.5 w-2.5 border-r border-t border-primary/55"
    />
    <span
      aria-hidden
      className="pointer-events-none absolute bottom-1.5 left-1.5 h-2.5 w-2.5 border-b border-l border-primary/55"
    />
    <span
      aria-hidden
      className="pointer-events-none absolute bottom-1.5 right-1.5 h-2.5 w-2.5 border-b border-r border-primary/55"
    />
  </>
);

// ── One fiche on the bench ───────────────────────────────────────────────────

const BenchFiche: React.FC<{
  located: Located;
  side?: 'primary' | 'vs';
  /** Which electorate this column reads — the dimension the comparison varies. */
  electorateLabel: string;
  onCompare?: () => void;
  onClose?: () => void;
}> = ({ located, side = 'primary', electorateLabel, onCompare, onClose }) => {
  const { t } = useTranslation('playground');
  const { family, group, experiment } = located;
  const Body = experiment.Body;
  // Single-fiche groups repeat their group title as the experiment title, and
  // the matrix/gallery paint their own full header — never say a name twice.
  const kicker =
    t(group.titleKey) === t(experiment.titleKey) ? t(family.labelKey) : t(group.titleKey);
  return (
    <section
      data-testid={side === 'vs' ? 'lab-bench-vs' : 'lab-bench'}
      className="relative min-w-0 rounded-md border border-primary/25 bg-card shadow-sm"
    >
      <Corners />
      <header className="flex items-start justify-between gap-3 border-b border-primary/15 bg-muted/30 px-4 py-2.5">
        <div className="min-w-0">
          <p className="truncate font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
            {kicker}
          </p>
          {!experiment.ownHeader && (
            <h2 className="mt-0.5 font-display text-lg font-semibold leading-tight tracking-tight">
              {t(experiment.titleKey)}
            </h2>
          )}
          {/* The electorate this column is measured on — the axis the face-à-face
              holds one side against the other. */}
          <span
            data-testid={`lab-elec-label-${side}`}
            className="mt-1 inline-flex max-w-full items-center gap-1 truncate rounded-full border border-primary/20 bg-primary/5 px-2 py-0.5 font-mono text-[0.6rem] uppercase tracking-[0.1em] text-primary"
          >
            <Users aria-hidden className="h-3 w-3 shrink-0" />
            <span className="truncate">{electorateLabel}</span>
          </span>
        </div>
        {onCompare && (
          <Button
            data-testid="lab-compare"
            variant="outline"
            size="sm"
            className="shrink-0 gap-1.5"
            onClick={onCompare}
          >
            <Columns2 aria-hidden className="h-3.5 w-3.5" />
            {t('lab.compareElec')}
          </Button>
        )}
        {onClose && (
          <Button
            data-testid="lab-compare-close"
            variant="ghost"
            size="sm"
            className="shrink-0 gap-1 text-muted-foreground"
            onClick={onClose}
            aria-label={t('lab.compareStop')}
          >
            <X aria-hidden className="h-3.5 w-3.5" />
          </Button>
        )}
      </header>
      {group.introKey && (
        <p className="border-b border-border/40 px-4 py-2 text-[0.7rem] leading-relaxed text-muted-foreground/80">
          {t(group.introKey)}
        </p>
      )}
      <div className="p-4">
        <React.Suspense fallback={<AnchorFallback />}>
          <Body />
        </React.Suspense>
      </div>
    </section>
  );
};

// ── The page ─────────────────────────────────────────────────────────────────

const LaboratoireContent: React.FC = () => {
  const { t } = useTranslation('playground');
  const [searchParams, setSearchParams] = useSearchParams();
  const { config } = useElection();
  const { playground } = usePlayground();

  const expId = searchParams.get('exp') ?? DEFAULT_EXPERIMENT;
  const active = locateExperiment(expId) ?? locateExperiment(DEFAULT_EXPERIMENT)!;
  // Comparison axis: the SAME fiche read on a second electorate (a preset), so the
  // phenomenon is held constant and only the electorate varies. `vsElec` is the
  // preset id; unknown ids fall back to no comparison.
  const vsElecRaw = searchParams.get('vsElec');
  const vsElec = vsElecRaw && ELECTORATE_PRESETS[vsElecRaw] ? vsElecRaw : null;

  // Which family's catalogue is open — follows the active fiche, but browsing
  // another family must not clear the bench.
  const [familyId, setFamilyId] = React.useState<FamilyId>(active.family.id);
  // Whether the "compare on another electorate" picker is showing.
  const [pickingElec, setPickingElec] = React.useState(false);

  const family = LAB_FAMILIES.find((f) => f.id === familyId) ?? LAB_FAMILIES[0];

  const setBench = (exp: string, vsElecNext: string | null) => {
    const params: Record<string, string> = { exp };
    if (vsElecNext) params.vsElec = vsElecNext;
    setSearchParams(params, { replace: true });
  };

  // A chip switches the fiche; column B (if open) follows onto the new fiche, so
  // the two columns always show the SAME phenomenon on their two electorates.
  const pick = (id: string) => {
    track('lab_fiche_opened', { fiche: id });
    setBench(id, vsElec);
  };

  // Clicking a preset opens (or re-targets) column B; clicking the open one closes.
  const pickElec = (id: string) => {
    const next = id === vsElec ? null : id;
    if (next) track('lab_compare_opened', { fiche: active.experiment.id, electorate: next });
    setBench(active.experiment.id, next);
    setPickingElec(false);
  };

  // Electorate B: the current candidates, but the voter distribution swapped for
  // the chosen preset (a composed mixture). Read-only — the override freezes it.
  const configB: ElectionConfig = config;
  const presetB = vsElec ? ELECTORATE_PRESETS[vsElec] : null;
  const playgroundB: PlaygroundState | null = presetB
    ? {
        ...playground,
        electorate: {
          mode: 'composed',
          correlation: presetB.correlation,
          noise: playground.electorate.noise,
          communities: presetB.communities.map((c) => ({ ...c })),
        },
      }
    : null;

  return (
    <div className="container mx-auto max-w-6xl px-4 py-5">
      {/* ── Masthead ── */}
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('lab.eyebrow')}
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold tracking-tight sm:text-3xl">
            {t('lab.title')}
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {t('lab.intro')}
          </p>
        </div>
        <Link to="/playground" className="text-sm text-primary hover:underline">
          ← {t('lab.backToPlayground')}
        </Link>
      </header>

      {/* ── Family rail ── */}
      <div
        data-testid="lab-family-rail"
        role="radiogroup"
        aria-label={t('lab.title')}
        className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:flex lg:items-stretch"
      >
        {LAB_FAMILIES.map((f) => {
          const on = f.id === familyId;
          const Icon = FAMILY_ICON[f.id];
          return (
            <button
              key={f.id}
              type="button"
              role="radio"
              aria-checked={on}
              data-testid={`lab-family-${f.id}`}
              onClick={() => setFamilyId(f.id)}
              className={cn(
                'group flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-all',
                on
                  ? 'border border-primary/30 bg-card shadow-sm'
                  : 'border border-transparent hover:bg-muted/50'
              )}
            >
              <span
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors',
                  on
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-background text-muted-foreground group-hover:text-foreground'
                )}
              >
                <Icon aria-hidden className="h-3.5 w-3.5" />
              </span>
              <span
                className={cn(
                  'min-w-0 truncate text-sm transition-colors',
                  on
                    ? 'font-display font-semibold text-foreground'
                    : 'font-medium text-muted-foreground group-hover:text-foreground'
                )}
              >
                {t(f.labelKey)}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Catalogue of the active family ── */}
      <div
        data-testid="lab-catalogue"
        className="mt-3 rounded-xl border border-border bg-card/60 px-3 py-2.5"
      >
        <div className="flex flex-col gap-2.5">
          {family.groups.map((g) => (
            <div key={g.key}>
              <p className="mb-1.5 flex flex-wrap items-baseline gap-x-2 font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
                {t(g.titleKey)}
                {g.subtitleKey && (
                  <span className="normal-case tracking-normal text-muted-foreground/60">
                    {t(g.subtitleKey)}
                  </span>
                )}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {g.experiments.map((e) => {
                  const isActive = e.id === active.experiment.id;
                  return (
                    <button
                      key={e.id}
                      type="button"
                      data-testid={`chip-${e.id}`}
                      aria-pressed={isActive}
                      onMouseEnter={e.preload}
                      onFocus={e.preload}
                      onClick={() => pick(e.id)}
                      className={cn(
                        'rounded-md border px-2 py-1 text-xs transition-colors',
                        isActive
                          ? 'border-primary/60 bg-primary/10 font-medium text-foreground'
                          : 'border-border text-muted-foreground hover:bg-accent/40 hover:text-foreground'
                      )}
                    >
                      {t(e.titleKey)}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Electorate comparison picker: the same fiche on a second electorate ── */}
      {(pickingElec || vsElec) && (
        <div
          data-testid="lab-elec-picker"
          className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-primary/40 bg-primary/5 px-3 py-2"
        >
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-primary">
            {t('lab.comparePick')}
          </span>
          {Object.entries(ELECTORATE_PRESETS).map(([id, p]) => (
            <button
              key={id}
              type="button"
              data-testid={`lab-elec-${id}`}
              aria-pressed={id === vsElec}
              onClick={() => pickElec(id)}
              className={cn(
                'rounded-md border px-2 py-1 text-xs transition-colors',
                id === vsElec
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {/* ── L'établi ── */}
      <div className={cn('mt-3 grid grid-cols-1 gap-3', vsElec && 'xl:grid-cols-2')}>
        <BenchFiche
          located={active}
          electorateLabel={t('lab.elecCurrent')}
          onCompare={!vsElec ? () => setPickingElec((p) => !p) : undefined}
        />
        {vsElec && playgroundB && (
          <ElectorateOverrideProvider config={configB} playground={playgroundB}>
            <PlaygroundProvider>
              <BenchFiche
                located={active}
                side="vs"
                electorateLabel={presetB?.label ?? ''}
                onClose={() => setBench(active.experiment.id, null)}
              />
            </PlaygroundProvider>
          </ElectorateOverrideProvider>
        )}
      </div>
    </div>
  );
};

const LaboratoirePage: React.FC = () => {
  const { t } = useTranslation('playground');
  useMetaTags({
    title: `Vote Lab — ${t('lab.title')}`,
    description: t('lab.intro'),
  });

  return (
    <PlaygroundProvider>
      <LaboratoireContent />
    </PlaygroundProvider>
  );
};

export default LaboratoirePage;
