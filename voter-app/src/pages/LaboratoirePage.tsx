import React from 'react';
import { useTranslation } from 'react-i18next';
import ReportContentError from '../components/shared/ui/ReportContentError';
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
import { FoldedCorner, RiseWords } from '@/components/ui/slip';
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
import { hasWords, matchesQuery } from '../lib/labSearch';
import {
  LAB_FAMILIES,
  DEFAULT_EXPERIMENT,
  locateExperiment,
  type FamilyId,
  type LabExperiment,
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

// ── A fiche's chip: in the family's catalogue, and (with its family) in the search results ──

const FicheChip: React.FC<{
  experiment: LabExperiment;
  isActive: boolean;
  onPick: () => void;
  /** Named in the search results, where the chips of several families sit together. */
  familyLabel?: string;
}> = ({ experiment, isActive, onPick, familyLabel }) => {
  const { t } = useTranslation('playground');
  return (
    <button
      type="button"
      data-testid={`chip-${experiment.id}`}
      aria-pressed={isActive}
      onMouseEnter={experiment.preload}
      onFocus={experiment.preload}
      onClick={onPick}
      className={cn(
        'rounded-full border px-3 py-1 text-sm transition-colors motion-reduce:transition-none',
        familyLabel && 'flex items-baseline gap-2',
        isActive
          ? 'border-primary bg-primary font-semibold text-primary-foreground'
          : 'border-border bg-card text-foreground hover:border-primary/50'
      )}
    >
      {t(experiment.titleKey)}
      {familyLabel && (
        <span
          className={cn(
            'text-[0.72rem] font-normal',
            isActive ? 'text-primary-foreground/80' : 'text-muted-foreground'
          )}
        >
          {familyLabel}
        </span>
      )}
    </button>
  );
};

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
    // The bench is a slip: its corner is folded over, drawn rather than cut, so the
    // fiche's popovers and tooltips are never clipped. The column B one drops in.
    <section
      data-testid={side === 'vs' ? 'lab-bench-vs' : 'lab-bench'}
      className={cn(
        'relative min-w-0 border border-border bg-card',
        side === 'vs' && 'ballot-drop'
      )}
      style={side === 'vs' ? ({ '--tilt': '2deg' } as React.CSSProperties) : undefined}
    >
      <FoldedCorner size={28} />
      {/* Keyed on the fiche: each new one is laid down by the slip's slanted sweep. */}
      <div key={experiment.id} className="bench-wipe">
        <header className="flex items-start justify-between gap-3 border-b border-border py-4 pr-10 pl-5 sm:pl-6">
          <div className="min-w-0">
            <p className="truncate text-[15px] font-bold text-primary">{kicker}</p>
            {!experiment.ownHeader && (
              <h2 className="mt-1 font-display text-[30px] leading-[0.95] font-extrabold sm:text-[36px]">
                {t(experiment.titleKey)}
              </h2>
            )}
            {/* The electorate this column is measured on — the axis the face-à-face
              holds one side against the other. */}
            <span
              data-testid={`lab-elec-label-${side}`}
              // A fiche that ignores the electorate's mix says so, instead of wearing a label
              // that suggests the electorate shapes it (and Compare is not offered there).
              className="mt-2.5 inline-flex max-w-full items-center gap-1.5 truncate rounded-full border border-border bg-muted px-2.5 py-0.5 text-[0.78rem] font-semibold text-muted-foreground"
            >
              <Users aria-hidden className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">
                {experiment.readsElectorate ? electorateLabel : t('lab.elecIndependent')}
              </span>
            </span>
            {/* Why there is no Compare here, in text anyone reads (not a tooltip). */}
            {!experiment.readsElectorate && (
              <p
                data-testid="lab-elec-note"
                className="mt-1.5 max-w-prose text-[0.78rem] leading-snug text-muted-foreground"
              >
                {t('lab.elecIndependentNote')}
              </p>
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
          <p className="border-b border-border px-5 py-3 text-sm leading-relaxed text-muted-foreground sm:px-6">
            {t(group.introKey)}
          </p>
        )}
        <div className="p-5 sm:p-6">
          <React.Suspense fallback={<AnchorFallback />}>
            <Body />
          </React.Suspense>
        </div>
      </div>
      <footer className="border-t border-border px-5 py-2 text-right sm:px-6">
        {/* The electorate label says which column a compare-mode reader was on. */}
        <ReportContentError
          where={`lab:${experiment.id} @ ${experiment.readsElectorate ? electorateLabel : 'electorate-independent'}`}
        />
      </footer>
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
  // Only a fiche that reads the electorate's composition has a second column to show: on any other
  // the two would be identical, so a stale `vsElec` in a link is ignored there.
  const vsElecRaw = searchParams.get('vsElec');
  const vsElec =
    active.experiment.readsElectorate && vsElecRaw && ELECTORATE_PRESETS[vsElecRaw]
      ? vsElecRaw
      : null;

  // Which family's catalogue is open — follows the active fiche, but browsing
  // another family must not clear the bench.
  const [familyId, setFamilyId] = React.useState<FamilyId>(active.family.id);
  // Whether the "compare on another electorate" picker is showing.
  const [pickingElec, setPickingElec] = React.useState(false);

  const family = LAB_FAMILIES.find((f) => f.id === familyId) ?? LAB_FAMILIES[0];

  // The search box looks across every family at once; while it holds words, its results stand in
  // for the family's catalogue. Matching is on what the chips and groups say, in the active language.
  const [query, setQuery] = React.useState('');
  const searching = hasWords(query);
  const results = React.useMemo(
    () =>
      searching
        ? LAB_FAMILIES.flatMap((f) =>
            f.groups.flatMap((g) =>
              g.experiments
                .filter((e) =>
                  matchesQuery(`${t(e.titleKey)} ${t(g.titleKey)} ${t(f.labelKey)}`, query)
                )
                .map((e) => ({ family: f, group: g, experiment: e }))
            )
          )
        : [],
    [searching, query, t]
  );

  const setBench = (exp: string, vsElecNext: string | null) => {
    const params: Record<string, string> = { exp };
    if (vsElecNext) params.vsElec = vsElecNext;
    setSearchParams(params, { replace: true });
  };

  // A chip switches the fiche; column B (if open) follows onto the new fiche, so
  // the two columns always show the SAME phenomenon on their two electorates.
  const pick = (id: string) => {
    track('lab_fiche_opened', { fiche: id });
    // A picker armed on one fiche is not a pending question on the next.
    setPickingElec(false);
    setBench(id, locateExperiment(id)?.experiment.readsElectorate ? vsElec : null);
  };

  // A result opens its fiche and brings its family along, so closing the search lands on it.
  const pickResult = (located: Located) => {
    setFamilyId(located.family.id);
    pick(located.experiment.id);
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
    <div className="mx-auto max-w-6xl px-4 pt-14 pb-20 sm:px-6">
      {/* ── Masthead ── */}
      <header className="mb-10 flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
        <div className="flex max-w-3xl flex-col gap-4">
          <p className="home-up text-[15px] font-bold text-primary">{t('lab.eyebrow')}</p>
          <h1 className="font-display text-[clamp(52px,6.4vw,96px)] leading-[0.9] font-extrabold">
            <RiseWords text={t('lab.title')} delay={80} />
          </h1>
          <p
            className="home-up text-lg leading-relaxed text-muted-foreground"
            style={{ animationDelay: '200ms' }}
          >
            {t('lab.intro')}
          </p>
        </div>
        <Link
          to="/playground"
          className="home-up text-[15px] font-bold text-primary no-underline hover:underline"
          style={{ animationDelay: '260ms' }}
        >
          ← {t('lab.backToPlayground')}
        </Link>
      </header>

      {/* ── Search: across every family ── */}
      <div className="home-up mb-3" style={{ animationDelay: '280ms' }}>
        <input
          data-testid="lab-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setQuery('');
          }}
          placeholder={t('lab.search')}
          aria-label={t('lab.search')}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none sm:max-w-md"
        />
        {/* Heard when the count changes; seen as the results themselves. */}
        <p role="status" className="sr-only" data-testid="lab-search-count">
          {searching
            ? results.length > 0
              ? t('lab.searchResults', { count: results.length })
              : t('lab.searchEmpty', { q: query.trim(), interpolation: { escapeValue: false } })
            : ''}
        </p>
      </div>

      {/* ── Family rail ── */}
      <div
        data-testid="lab-family-rail"
        role="radiogroup"
        aria-label={t('lab.title')}
        className="home-up grid grid-cols-2 gap-1 border-b border-border sm:grid-cols-3 lg:flex lg:items-stretch"
        style={{ animationDelay: '300ms' }}
      >
        {LAB_FAMILIES.map((f) => {
          // While the search stands in for the catalogue, no family is the one being read.
          const on = !searching && f.id === familyId;
          const Icon = FAMILY_ICON[f.id];
          return (
            <button
              key={f.id}
              type="button"
              role="radio"
              aria-checked={on}
              data-testid={`lab-family-${f.id}`}
              onClick={() => {
                setQuery('');
                setFamilyId(f.id);
              }}
              className={cn(
                'group relative flex min-w-0 flex-1 items-center gap-2.5 rounded-t-lg px-3 py-2.5 text-left transition-colors motion-reduce:transition-none',
                on
                  ? 'bg-card after:absolute after:inset-x-2 after:-bottom-px after:h-[3px] after:rounded-full after:bg-primary'
                  : 'hover:bg-muted/60'
              )}
            >
              <span
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors motion-reduce:transition-none',
                  on
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground group-hover:text-foreground'
                )}
              >
                <Icon aria-hidden className="h-4 w-4" strokeWidth={1.75} />
              </span>
              <span
                className={cn(
                  'min-w-0 text-[15px] leading-tight font-semibold transition-colors motion-reduce:transition-none',
                  on ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'
                )}
              >
                {t(f.labelKey)}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Catalogue of the active family ── */}
      <div data-testid="lab-catalogue" className="mt-2">
        {searching ? (
          <div
            data-testid="lab-search-results"
            className="flex flex-col border-b border-border py-4"
          >
            {results.length === 0 ? (
              <p data-testid="lab-search-empty" className="text-sm text-muted-foreground">
                {t('lab.searchEmpty', { q: query.trim(), interpolation: { escapeValue: false } })}
              </p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {results.map((r) => (
                  <li key={r.experiment.id}>
                    <FicheChip
                      experiment={r.experiment}
                      isActive={r.experiment.id === active.experiment.id}
                      onPick={() => pickResult(r)}
                      familyLabel={t(r.family.labelKey)}
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div key={family.id} className="flex flex-col">
            {family.groups.map((g, gi) => (
              <div
                key={g.key}
                className="home-up flex flex-col gap-2.5 border-b border-border py-4 lg:flex-row lg:gap-8"
                style={{ animationDelay: `${gi * 70}ms` }}
              >
                <p className="flex shrink-0 flex-col lg:w-56">
                  <span className="font-display text-[22px] leading-none font-extrabold">
                    {t(g.titleKey)}
                  </span>
                  {g.subtitleKey && (
                    <span className="mt-1 text-sm text-muted-foreground">{t(g.subtitleKey)}</span>
                  )}
                </p>
                <div className="flex flex-wrap content-start gap-1.5">
                  {g.experiments.map((e) => (
                    <FicheChip
                      key={e.id}
                      experiment={e}
                      isActive={e.id === active.experiment.id}
                      onPick={() => pick(e.id)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Electorate comparison picker: the same fiche on a second electorate ── */}
      {(pickingElec || vsElec) && active.experiment.readsElectorate && (
        <div
          data-testid="lab-elec-picker"
          className="home-up mt-6 flex flex-wrap items-center gap-2 rounded-2xl bg-envelope px-4 py-3"
        >
          <span className="mr-1 text-[15px] font-bold text-primary">{t('lab.comparePick')}</span>
          {Object.entries(ELECTORATE_PRESETS).map(([id, p]) => (
            <button
              key={id}
              type="button"
              data-testid={`lab-elec-${id}`}
              aria-pressed={id === vsElec}
              onClick={() => pickElec(id)}
              className={cn(
                'rounded-full border px-3 py-1 text-sm transition-colors motion-reduce:transition-none',
                id === vsElec
                  ? 'border-primary bg-primary font-semibold text-primary-foreground'
                  : 'border-border bg-card text-foreground hover:border-primary/50'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {/* ── L'établi ── */}
      <div className={cn('mt-8 grid grid-cols-1 gap-5', vsElec && 'xl:grid-cols-2')}>
        <BenchFiche
          located={active}
          electorateLabel={t('lab.elecCurrent')}
          onCompare={
            !vsElec && active.experiment.readsElectorate
              ? () => setPickingElec((p) => !p)
              : undefined
          }
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
