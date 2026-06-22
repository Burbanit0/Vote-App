import React from 'react';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';

// BehaviorAnchor — the "Comportement des électeurs" family, re-homed next to the
// behaviour <select> in the Setup rail (it deepens that very knob). Every panel
// reads the shared electorate via useElection(); only their phenomenon-specific
// knobs are local. All lazy + Collapsible-gated, so mounting this anchor adds no
// compute until a Leaf is opened.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk (these panels pull in Recharts) before the click.

const BehavioralBiasPanel = lazyWithPreload(() => import('../../shared/BehavioralBiasPanel'));
const CascadePanel = lazyWithPreload(() => import('../../shared/CascadePanel'));
const AffectivePolarizationPanel = lazyWithPreload(
  () => import('../../shared/AffectivePolarizationPanel')
);
const ShyVoterPanel = lazyWithPreload(() => import('../../shared/ShyVoterPanel'));
const ElectoralFatiguePanel = lazyWithPreload(() => import('../../shared/ElectoralFatiguePanel'));
const ChoiceOverloadPanel = lazyWithPreload(() => import('../../shared/ChoiceOverloadPanel'));
const CompulsoryVotingPanel = lazyWithPreload(() => import('../../shared/CompulsoryVotingPanel'));
const DemographicTurnoutPanel = lazyWithPreload(
  () => import('../../shared/DemographicTurnoutPanel')
);

const BehaviorAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Comment le <strong>comportement</strong> réel des électeurs (biais, cascades, fatigue,
      participation différentielle…) déplace le résultat sur le même électorat. Chaque module se
      calcule à la demande.
    </p>
    <Leaf
      title="📊 Biais de vote (ordre, ancrage)"
      testid="beh-biases"
      prefetch={BehavioralBiasPanel.preload}
    >
      <BehavioralBiasPanel />
    </Leaf>
    <Leaf title="🌊 Cascade d’information" testid="beh-cascade" prefetch={CascadePanel.preload}>
      <CascadePanel />
    </Leaf>
    <Leaf
      title="🔥 Polarisation affective"
      testid="beh-affective"
      prefetch={AffectivePolarizationPanel.preload}
    >
      <AffectivePolarizationPanel />
    </Leaf>
    <Leaf
      title="🤐 Électeur timide (effet Bradley)"
      testid="beh-shyvoter"
      prefetch={ShyVoterPanel.preload}
    >
      <ShyVoterPanel />
    </Leaf>
    <Leaf
      title="😮‍💨 Fatigue électorale"
      testid="beh-fatigue"
      prefetch={ElectoralFatiguePanel.preload}
    >
      <ElectoralFatiguePanel />
    </Leaf>
    <Leaf
      title="🤯 Surcharge de choix"
      testid="beh-overload"
      prefetch={ChoiceOverloadPanel.preload}
    >
      <ChoiceOverloadPanel />
    </Leaf>
    <Leaf
      title="🗳️ Vote obligatoire"
      testid="beh-compulsory"
      prefetch={CompulsoryVotingPanel.preload}
    >
      <CompulsoryVotingPanel />
    </Leaf>
    <Leaf
      title="👥 Participation par démographie"
      testid="beh-demographic"
      prefetch={DemographicTurnoutPanel.preload}
    >
      <DemographicTurnoutPanel />
    </Leaf>
  </div>
);

export default BehaviorAnchor;
