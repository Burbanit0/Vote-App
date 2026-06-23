import React from 'react';
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

const CampaignAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Le scrubber ci-dessus montre <strong>une</strong> trajectoire (les candidats dérivent vers
      l’électeur médian). Ces quatre étapes l’approfondissent : l’équilibre visé, l’effet des
      sondages, l’impact de la polarisation, puis l’évolution du système de partis sur plusieurs
      élections.
    </p>
    <Leaf
      title="① 📐 Vers quel équilibre ? (Hotelling-Downs)"
      testid="dyn-hotelling"
      prefetch={HotellingPanel.preload}
    >
      <HotellingPanel />
    </Leaf>
    <Leaf
      title="② 📣 Effet des sondages (sensibilité de campagne)"
      testid="dyn-campaign"
      prefetch={CampaignSensitivityPanel.preload}
    >
      <CampaignSensitivityPanel />
    </Leaf>
    <Leaf
      title="③ ↔️ Électorat polarisé (qualité du résultat)"
      testid="dyn-polarization"
      prefetch={PolarizationPanel.preload}
    >
      <PolarizationPanel />
    </Leaf>
    <Leaf
      title="④ 🏳️ Évolution des partis (Duverger sur la durée)"
      testid="dyn-party"
      prefetch={PartyDynamicsPanel.preload}
    >
      <PartyDynamicsPanel />
    </Leaf>
  </div>
);

export default CampaignAnchor;
