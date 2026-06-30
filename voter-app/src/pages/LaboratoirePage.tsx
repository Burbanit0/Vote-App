import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { useMetaTags } from '../hooks/useMetaTags';
import {
  PlaygroundProvider,
  usePlaygroundCtx,
} from '../components/playground/PlaygroundController';
import Collapsible from '../components/playground/Collapsible';
import { AnchorFallback } from '../components/playground/playgroundFields';
import InstrumentPanel from '../components/playground/InstrumentPanel';

const MethodsMatrix = React.lazy(() => import('../components/lab/MethodsMatrix'));

const MechanismsAnchor = React.lazy(
  () => import('../components/playground/anchors/MechanismsAnchor')
);
const SystemsAnchor = React.lazy(() => import('../components/playground/anchors/SystemsAnchor'));
const AnalysisAnchor = React.lazy(() => import('../components/playground/anchors/AnalysisAnchor'));
const TheoryAnchor = React.lazy(() => import('../components/playground/anchors/TheoryAnchor'));
const ResultsAnchor = React.lazy(() => import('../components/playground/anchors/ResultsAnchor'));
const CampaignAnchor = React.lazy(() => import('../components/playground/anchors/CampaignAnchor'));
const TemporalDynamicsAnchor = React.lazy(
  () => import('../components/campaign/TemporalDynamicsAnchor')
);
const BehavioralRealismAnchor = React.lazy(
  () => import('../components/campaign/BehavioralRealismAnchor')
);
const BallotConfigPanel = React.lazy(() => import('../components/playground/BallotConfigPanel'));
const StrategyLabPanel = React.lazy(() => import('../components/playground/StrategyLabPanel'));
const ValuesLabPanel = React.lazy(() => import('../components/playground/ValuesLabPanel'));

type SectionKey =
  | 'ballot'
  | 'strategy'
  | 'values'
  | 'mechanisms'
  | 'systems'
  | 'campaign'
  | 'temporal'
  | 'behavioral'
  | 'analysis'
  | 'theory'
  | 'results';

const SECTION_COMPONENTS: Record<SectionKey, React.LazyExoticComponent<React.FC>> = {
  ballot: BallotConfigPanel,
  strategy: StrategyLabPanel,
  values: ValuesLabPanel,
  mechanisms: MechanismsAnchor,
  systems: SystemsAnchor,
  campaign: CampaignAnchor,
  temporal: TemporalDynamicsAnchor,
  behavioral: BehavioralRealismAnchor,
  analysis: AnalysisAnchor,
  theory: TheoryAnchor,
  results: ResultsAnchor,
};

const GROUPS: {
  key: string;
  labelKey: string;
  kicker: string;
  sections: SectionKey[];
}[] = [
  {
    key: 'rules',
    labelKey: 'lab.groups.rules',
    kicker: '① ',
    sections: ['ballot', 'strategy', 'values'],
  },
  {
    key: 'systems',
    labelKey: 'lab.groups.systems',
    kicker: '② ',
    sections: ['mechanisms', 'systems'],
  },
  {
    key: 'dynamics',
    labelKey: 'lab.groups.dynamics',
    kicker: '③ ',
    sections: ['campaign', 'temporal', 'behavioral'],
  },
  {
    key: 'theory',
    labelKey: 'lab.groups.theory',
    kicker: '④ ',
    sections: ['theory', 'analysis', 'results'],
  },
];

const LaboratoireContent: React.FC = () => {
  const { t } = useTranslation('playground');
  usePlaygroundCtx();

  return (
    <div className="container mx-auto max-w-6xl px-4 py-6">
      {/* ── Page header ── */}
      <div className="mb-5">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
          {t('lab.eyebrow')}
        </p>
        <h1 className="mt-1 font-display text-2xl font-bold tracking-tight sm:text-3xl">
          {t('lab.title')}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          {t('lab.intro')}
        </p>
        <Link to="/playground" className="mt-2 inline-block text-sm text-primary hover:underline">
          ← {t('lab.backToPlayground')}
        </Link>
      </div>

      {/* The instrument stays docked in this rail while you scroll the sections on the
          right — every effect below reads off this same live map, instead of each
          section floating with no shared visual. */}
      <div className="lg:grid lg:grid-cols-[22rem_1fr] lg:items-start lg:gap-6">
        <div className="mb-8 lg:sticky lg:top-4 lg:mb-0">
          <InstrumentPanel />
          <p className="mt-2 text-[0.7rem] leading-snug text-muted-foreground">
            {t('lab.instrumentHint')}
          </p>
        </div>

        <div className="flex flex-col gap-8">
          {/* ── Methods matrix ── */}
          <React.Suspense fallback={<AnchorFallback />}>
            <MethodsMatrix />
          </React.Suspense>

          {/* ── Grouped sections ── */}
          <div className="flex flex-col gap-8">
            {GROUPS.map(({ key, labelKey, kicker, sections }) => (
              <div key={key} id={`lab-group-${key}`}>
                {/* Group header */}
                <div className="mb-3 flex items-center gap-2">
                  <span className="font-mono text-[0.68rem] uppercase tracking-[0.2em] text-muted-foreground">
                    {kicker}
                  </span>
                  <h2 className="font-display text-base font-semibold tracking-tight">
                    {t(labelKey)}
                  </h2>
                  <div className="flex-1 border-t border-border" />
                </div>

                {/* Sections in this group */}
                <div className="flex flex-col gap-2.5">
                  {sections.map((sectionKey) => {
                    const Component = SECTION_COMPONENTS[sectionKey];
                    return (
                      <Collapsible
                        key={sectionKey}
                        title={t(`lab.${sectionKey}.title`)}
                        subtitle={t(`lab.${sectionKey}.subtitle`)}
                        testid={`lab-${sectionKey}`}
                      >
                        <React.Suspense fallback={<AnchorFallback />}>
                          <Component />
                        </React.Suspense>
                      </Collapsible>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
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
