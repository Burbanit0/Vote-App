import React from 'react';
import Leaf from './Leaf';

// BehaviorAnchor — the "Comportement des électeurs" family, re-homed next to the
// behaviour <select> in the Setup rail (it deepens that very knob). Every panel
// reads the shared electorate via useElection(); only their phenomenon-specific
// knobs are local. All lazy + Collapsible-gated, so mounting this anchor adds no
// compute until a Leaf is opened.

const BehavioralBiasPanel = React.lazy(() => import('../../shared/BehavioralBiasPanel'));
const CascadePanel = React.lazy(() => import('../../shared/CascadePanel'));
const AffectivePolarizationPanel = React.lazy(
  () => import('../../shared/AffectivePolarizationPanel')
);
const ShyVoterPanel = React.lazy(() => import('../../shared/ShyVoterPanel'));
const ElectoralFatiguePanel = React.lazy(() => import('../../shared/ElectoralFatiguePanel'));
const ChoiceOverloadPanel = React.lazy(() => import('../../shared/ChoiceOverloadPanel'));
const CompulsoryVotingPanel = React.lazy(() => import('../../shared/CompulsoryVotingPanel'));
const DemographicTurnoutPanel = React.lazy(() => import('../../shared/DemographicTurnoutPanel'));

const BehaviorAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Comment le <strong>comportement</strong> réel des électeurs (biais, cascades, fatigue,
      participation différentielle…) déplace le résultat sur le même électorat. Chaque module se
      calcule à la demande.
    </p>
    <Leaf title="📊 Biais de vote (ordre, ancrage)" testid="beh-biases">
      <BehavioralBiasPanel />
    </Leaf>
    <Leaf title="🌊 Cascade d’information" testid="beh-cascade">
      <CascadePanel />
    </Leaf>
    <Leaf title="🔥 Polarisation affective" testid="beh-affective">
      <AffectivePolarizationPanel />
    </Leaf>
    <Leaf title="🤐 Électeur timide (effet Bradley)" testid="beh-shyvoter">
      <ShyVoterPanel />
    </Leaf>
    <Leaf title="😮‍💨 Fatigue électorale" testid="beh-fatigue">
      <ElectoralFatiguePanel />
    </Leaf>
    <Leaf title="🤯 Surcharge de choix" testid="beh-overload">
      <ChoiceOverloadPanel />
    </Leaf>
    <Leaf title="🗳️ Vote obligatoire" testid="beh-compulsory">
      <CompulsoryVotingPanel />
    </Leaf>
    <Leaf title="👥 Participation par démographie" testid="beh-demographic">
      <DemographicTurnoutPanel />
    </Leaf>
  </div>
);

export default BehaviorAnchor;
