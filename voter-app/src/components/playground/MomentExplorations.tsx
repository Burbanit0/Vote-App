import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from './PlaygroundController';
import { AnchorFallback } from './playgroundFields';
import Collapsible from './Collapsible';

// MomentExplorations — the deep dives, attached to the moment they deepen rather
// than stacked at the bottom of every page. Full-width below the instrument (the
// charts need the room), lazy + collapsed so first paint mounts none of them.
//   ② Méthode → other procedures (leader) / electoral systems (parliament)
//   ⑤ Bilan   → the full tally, the deep analysis, and the underlying theory
const MechanismsAnchor = React.lazy(() => import('./anchors/MechanismsAnchor'));
const AnalysisAnchor = React.lazy(() => import('./anchors/AnalysisAnchor'));
const TheoryAnchor = React.lazy(() => import('./anchors/TheoryAnchor'));
const SystemsAnchor = React.lazy(() => import('./anchors/SystemsAnchor'));
const ResultsAnchor = React.lazy(() => import('./anchors/ResultsAnchor'));

const MomentExplorations: React.FC = () => {
  const { activeMoment, mode } = usePlaygroundCtx();
  const { t } = useTranslation('playground');

  let body: React.ReactNode = null;

  if (activeMoment === 'method') {
    body =
      mode === 'leader' ? (
        <Collapsible
          title={t('anchors.mechanisms.title')}
          subtitle={t('anchors.mechanisms.subtitle')}
          testid="anchor-mechanisms"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <MechanismsAnchor />
          </React.Suspense>
        </Collapsible>
      ) : (
        <Collapsible
          title={t('anchors.systems.title')}
          subtitle={t('anchors.systems.subtitle')}
          testid="anchor-systems"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <SystemsAnchor />
          </React.Suspense>
        </Collapsible>
      );
  } else if (activeMoment === 'bilan') {
    body = (
      <>
        <Collapsible
          title={t('anchors.results.title')}
          subtitle={t('anchors.results.subtitle')}
          testid="anchor-results"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <ResultsAnchor />
          </React.Suspense>
        </Collapsible>
        <Collapsible
          title={t('anchors.analysis.title')}
          subtitle={t('anchors.analysis.subtitle')}
          testid="anchor-analysis"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <AnalysisAnchor />
          </React.Suspense>
        </Collapsible>
        <Collapsible
          title={t('anchors.theory.title')}
          subtitle={t('anchors.theory.subtitle')}
          testid="anchor-theory"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <TheoryAnchor />
          </React.Suspense>
        </Collapsible>
      </>
    );
  }

  if (!body) return null;

  return (
    <section className="mt-4 flex flex-col gap-3">
      <p className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t('explore.heading')}
      </p>
      {body}
    </section>
  );
};

export default MomentExplorations;
