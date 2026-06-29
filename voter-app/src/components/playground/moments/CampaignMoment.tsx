import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@/components/ui/card';
import { usePlaygroundCtx } from '../PlaygroundController';
import CampaignTimeline from '../../campaign/CampaignTimeline';

// Moment ④ Campagne — how the vote reacts over time. The timeline reads the shared
// J0 electorate; the one explicit write-back is "pin this instant" as the new
// baseline. Full-width: it replaces the static instrument for this moment.
// The deep per-phenomenon panels (trajectory, temporal mechanisms, behavioral
// realism) live in /laboratoire — same components, reachable on demand.
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
    </div>
  );
};

export default CampaignMoment;
