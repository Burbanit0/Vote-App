import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { Columns2, X, Scale, Swords, Landmark, Activity, FlaskConical } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import {
  PlaygroundProvider,
  usePlaygroundCtx,
} from '../components/playground/PlaygroundController';
import { AnchorFallback, selectCls } from '../components/playground/playgroundFields';
import { useVotingLabels } from '../hooks/useVotingLabels';
import { LEADER_RULES } from '../lib/scorecard';
import { candidateColor } from '../lib/palette';
import { track } from '../lib/analytics';
import {
  LAB_FAMILIES,
  DEFAULT_EXPERIMENT,
  locateExperiment,
  type FamilyId,
  type Located,
} from '../components/lab/labCatalog';
import type { Rule } from '../lib/playgroundVoting';

// LaboratoirePage — the specimen bench. The old page stacked 4 groups × 11
// sections × ~5 sub-accordions next to a 22rem sticky sidebar: everything was
// somewhere, nothing was anywhere. The redesign is the playground's own grammar
// extended to a collection:
//
//   family rail  →  électorat strip  →  catalogue of fiches  →  ONE full-width
//   bench (l'établi), with "Comparer" splitting it into two fiches that read the
//   SAME shared electorate.
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

// ── Électorat strip — the shared frame every fiche reads ────────────────────

const ElectorateStrip: React.FC = () => {
  const { t } = useTranslation('playground');
  const { config, leaderRule, setLeaderRule } = usePlaygroundCtx();
  const { ruleLabels } = useVotingLabels();
  return (
    // Reads as the same instrument's telemetry as the Playground's scope status
    // line (tinted mono strip), because it IS the same electorate — every fiche
    // below is measured on it.
    <div
      data-testid="lab-electorate-strip"
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border border-primary/15 bg-muted/30 px-3 py-2"
    >
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
        {config.candidates.map((c, i) => (
          <span key={c.name} className="flex items-center gap-1.5 text-xs">
            <span
              aria-hidden
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: candidateColor(i) }}
            />
            {c.name}
          </span>
        ))}
        <span
          aria-hidden
          className="font-mono text-[0.6rem] uppercase tracking-[0.12em] text-border"
        >
          ·
        </span>
        <span className="font-mono text-[0.6rem] uppercase tracking-[0.12em] text-muted-foreground">
          {t('lab.strip.voters', { n: config.num_voters })}
        </span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <label className="flex items-center gap-1.5 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-muted-foreground">
          {t('lab.strip.rule')}
          <select
            data-testid="lab-rule-select"
            className={cn(selectCls, 'h-7 w-auto py-0 text-xs normal-case tracking-normal')}
            value={leaderRule}
            onChange={(e) => setLeaderRule(e.target.value as Rule)}
          >
            {LEADER_RULES.map((r) => (
              <option key={r} value={r}>
                {ruleLabels[r]}
              </option>
            ))}
          </select>
        </label>
        <Link to="/playground" className="shrink-0 text-xs text-primary hover:underline">
          {t('lab.strip.edit')}
        </Link>
      </div>
    </div>
  );
};

// ── One fiche on the bench ───────────────────────────────────────────────────

const BenchFiche: React.FC<{
  located: Located;
  side?: 'primary' | 'vs';
  onCompare?: () => void;
  onClose?: () => void;
}> = ({ located, side = 'primary', onCompare, onClose }) => {
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
            {t('lab.compare')}
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

  const expId = searchParams.get('exp') ?? DEFAULT_EXPERIMENT;
  const vsId = searchParams.get('vs');
  const active = locateExperiment(expId) ?? locateExperiment(DEFAULT_EXPERIMENT)!;
  const vs = vsId ? locateExperiment(vsId) : null;

  // Which family's catalogue is open — follows the active fiche, but browsing
  // another family must not clear the bench.
  const [familyId, setFamilyId] = React.useState<FamilyId>(active.family.id);
  // When armed, the next chip click fills the SECOND slot of the bench.
  const [pickingVs, setPickingVs] = React.useState(false);

  const family = LAB_FAMILIES.find((f) => f.id === familyId) ?? LAB_FAMILIES[0];

  const setBench = (exp: string, vsNext: string | null) => {
    const params: Record<string, string> = { exp };
    if (vsNext) params.vs = vsNext;
    setSearchParams(params, { replace: true });
  };

  const pick = (id: string) => {
    if (pickingVs) {
      if (id !== active.experiment.id) {
        track('lab_compare_opened', { fiche: active.experiment.id, vs: id });
        setBench(active.experiment.id, id);
      }
      setPickingVs(false);
    } else {
      track('lab_fiche_opened', { fiche: id });
      setBench(id, vs && vs.experiment.id !== id ? vs.experiment.id : null);
    }
  };

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
        className={cn(
          'mt-3 rounded-xl border bg-card/60 px-3 py-2.5',
          pickingVs ? 'border-primary/50' : 'border-border'
        )}
      >
        {pickingVs && (
          <p
            data-testid="lab-compare-hint"
            className="mb-2 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
          >
            {t('lab.comparePick')}
          </p>
        )}
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
                  const isVs = vs?.experiment.id === e.id;
                  return (
                    <button
                      key={e.id}
                      type="button"
                      data-testid={`chip-${e.id}`}
                      aria-pressed={isActive || isVs}
                      onMouseEnter={e.preload}
                      onFocus={e.preload}
                      onClick={() => pick(e.id)}
                      className={cn(
                        'rounded-md border px-2 py-1 text-xs transition-colors',
                        isActive
                          ? 'border-primary/60 bg-primary/10 font-medium text-foreground'
                          : isVs
                            ? 'border-primary/30 bg-accent/50 text-foreground'
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

      {/* ── Électorat strip — the shared frame ── */}
      <div className="mt-3">
        <ElectorateStrip />
      </div>

      {/* ── L'établi ── */}
      <div className={cn('mt-3 grid grid-cols-1 gap-3', vs && 'xl:grid-cols-2')}>
        <BenchFiche located={active} onCompare={!vs ? () => setPickingVs((p) => !p) : undefined} />
        {vs && (
          <BenchFiche located={vs} side="vs" onClose={() => setBench(active.experiment.id, null)} />
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
