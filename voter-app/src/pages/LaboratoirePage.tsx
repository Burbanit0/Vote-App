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

const SECTIONS = [
  {
    key: 'ballot',
    titleKey: 'lab.ballot.title',
    subtitleKey: 'lab.ballot.subtitle',
    Component: BallotConfigPanel,
  },
  {
    key: 'mechanisms',
    titleKey: 'lab.mechanisms.title',
    subtitleKey: 'lab.mechanisms.subtitle',
    Component: MechanismsAnchor,
  },
  {
    key: 'systems',
    titleKey: 'lab.systems.title',
    subtitleKey: 'lab.systems.subtitle',
    Component: SystemsAnchor,
  },
  {
    key: 'campaign',
    titleKey: 'lab.campaign.title',
    subtitleKey: 'lab.campaign.subtitle',
    Component: CampaignAnchor,
  },
  {
    key: 'temporal',
    titleKey: 'lab.temporal.title',
    subtitleKey: 'lab.temporal.subtitle',
    Component: TemporalDynamicsAnchor,
  },
  {
    key: 'behavioral',
    titleKey: 'lab.behavioral.title',
    subtitleKey: 'lab.behavioral.subtitle',
    Component: BehavioralRealismAnchor,
  },
  {
    key: 'analysis',
    titleKey: 'lab.analysis.title',
    subtitleKey: 'lab.analysis.subtitle',
    Component: AnalysisAnchor,
  },
  {
    key: 'theory',
    titleKey: 'lab.theory.title',
    subtitleKey: 'lab.theory.subtitle',
    Component: TheoryAnchor,
  },
  {
    key: 'results',
    titleKey: 'lab.results.title',
    subtitleKey: 'lab.results.subtitle',
    Component: ResultsAnchor,
  },
] as const;

const LaboratoireContent: React.FC = () => {
  const { t } = useTranslation('playground');
  usePlaygroundCtx();

  return (
    <div className="container mx-auto max-w-5xl px-4 py-6">
      <div className="mb-6">
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

      <div className="flex flex-col gap-3">
        {SECTIONS.map(({ key, titleKey, subtitleKey, Component }) => (
          <Collapsible
            key={key}
            title={t(titleKey)}
            subtitle={t(subtitleKey)}
            testid={`lab-${key}`}
          >
            <React.Suspense fallback={<AnchorFallback />}>
              <Component />
            </React.Suspense>
          </Collapsible>
        ))}
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
