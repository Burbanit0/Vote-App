import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@/components/ui/card';
import { usePlaygroundCtx } from '../PlaygroundController';
import { AnchorFallback } from '../playgroundFields';
import Collapsible from '../Collapsible';
import CampaignTimeline from '../../campaign/CampaignTimeline';

// The deep per-phenomenon panels (formerly the standalone /campagne page) stay
// reachable but demoted + lazy, never competing with the timeline instrument.
const CampaignAnchor = React.lazy(() => import('../anchors/CampaignAnchor'));
const TemporalDynamicsAnchor = React.lazy(() => import('../../campaign/TemporalDynamicsAnchor'));
const BehavioralRealismAnchor = React.lazy(() => import('../../campaign/BehavioralRealismAnchor'));

// Moment ④ Campagne — how the vote reacts over time. The timeline reads the shared
// J0 electorate; the one explicit write-back is "pin this instant" as the new
// baseline. Full-width: it replaces the static instrument for this moment.
const CampaignMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { config, playground, pinToPlayground } = usePlaygroundCtx();

  if (config.candidates.length === 0) {
    return (
      <Card data-testid="moment-campaign-panel">
        <CardContent className="p-3">
          <p className="p-2 text-sm text-muted-foreground">{t('campaign.emptyPrompt')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div data-testid="moment-campaign-panel" className="flex flex-col gap-4">
      <Card>
        <CardContent className="p-3">
          <CampaignTimeline config={config} playground={playground} onPin={pinToPlayground} />
        </CardContent>
      </Card>

      <Collapsible
        title={t('campaign.deepTitle')}
        subtitle={t('campaign.deepSub')}
        testid="campaign-explorations"
      >
        <div className="flex flex-col gap-5">
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{t('campaign.deepTrajectory')}</h3>
            <React.Suspense fallback={<AnchorFallback />}>
              <CampaignAnchor />
            </React.Suspense>
          </section>
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{t('campaign.deepMechanisms')}</h3>
            <React.Suspense fallback={<AnchorFallback />}>
              <TemporalDynamicsAnchor />
            </React.Suspense>
          </section>
          <section className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{t('campaign.deepRealism')}</h3>
            <React.Suspense fallback={<AnchorFallback />}>
              <BehavioralRealismAnchor />
            </React.Suspense>
          </section>
        </div>
      </Collapsible>
    </div>
  );
};

export default CampaignMoment;
