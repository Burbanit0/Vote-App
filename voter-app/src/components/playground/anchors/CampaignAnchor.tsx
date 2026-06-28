import React from 'react';
import { useTranslation } from 'react-i18next';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';

// CampaignAnchor — the "Espace & dynamiques" Lab family, re-framed as one
// narrative around the live campaign scrubber (J0→J30 drift to the median).
// Where the scrubber shows a single trajectory, these deepen it in order:
//   1. where do rational candidates *converge*? (Hotelling–Downs equilibrium)
//   2. how do polls *perturb* that trajectory? (campaign sensitivity)
//   3. how does a more *polarized* electorate degrade the result? (Esteban-Ray)
//   4. how does the party system *evolve* over repeated elections? (Duverger)
// All lazy + Collapsible-gated — no compute until a step is opened.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const HotellingPanel = lazyWithPreload(() => import('../../shared/HotellingPanel'));
const CampaignSensitivityPanel = lazyWithPreload(
  () => import('../../shared/CampaignSensitivityPanel')
);
const PolarizationPanel = lazyWithPreload(() => import('../../shared/PolarizationPanel'));
const PartyDynamicsPanel = lazyWithPreload(() => import('../../shared/PartyDynamicsPanel'));

const CampaignAnchor: React.FC = () => {
  const { t } = useTranslation('playground');
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('anchorBody.campaign.intro')}</p>
      <Leaf
        title={t('anchorBody.campaign.hotelling')}
        testid="dyn-hotelling"
        prefetch={HotellingPanel.preload}
      >
        <HotellingPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.campaign.campaign')}
        testid="dyn-campaign"
        prefetch={CampaignSensitivityPanel.preload}
      >
        <CampaignSensitivityPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.campaign.polarization')}
        testid="dyn-polarization"
        prefetch={PolarizationPanel.preload}
      >
        <PolarizationPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.campaign.party')}
        testid="dyn-party"
        prefetch={PartyDynamicsPanel.preload}
      >
        <PartyDynamicsPanel />
      </Leaf>
    </div>
  );
};

export default CampaignAnchor;
