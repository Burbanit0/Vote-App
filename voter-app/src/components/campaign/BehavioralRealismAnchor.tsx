import React from 'react';
import Leaf from '../playground/anchors/Leaf';
import { lazyWithPreload } from '../../lib/lazyWithPreload';

// BehavioralRealismAnchor (C4) — the "réalisme comportemental" facette of the
// "Campagne & dynamique" page. These are the family-B phenomena: deformations of
// a SINGLE ballot caused by real voter behaviour (not time). They migrated off
// the playground (which now keeps only the idealized snapshot) so the page can
// tell the full "this result is an idealization — here is what perturbs it"
// story alongside the temporal mechanisms above.
//
// Each reads the shared electorate (state J0) via useElection(); all lazy +
// Collapsible-gated, so the page mounts nothing until a Leaf is opened.

const BehavioralBiasPanel = lazyWithPreload(() => import('../shared/BehavioralBiasPanel'));
const ShyVoterPanel = lazyWithPreload(() => import('../shared/ShyVoterPanel'));
const ChoiceOverloadPanel = lazyWithPreload(() => import('../shared/ChoiceOverloadPanel'));
const CompulsoryVotingPanel = lazyWithPreload(() => import('../shared/CompulsoryVotingPanel'));
const DemographicTurnoutPanel = lazyWithPreload(() => import('../shared/DemographicTurnoutPanel'));
const AffectivePolarizationPanel = lazyWithPreload(
  () => import('../shared/AffectivePolarizationPanel')
);

const BehavioralRealismAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Le résultat du playground suppose des électeurs idéaux. Ici, le <strong>comportement</strong>{' '}
      réel déforme <em>un même scrutin</em> — biais d’ordre, vote timide, surcharge de choix,
      participation différentielle, polarisation affective. Chaque module se calcule à la demande.
    </p>
    <Leaf
      title="📊 Biais de vote (ordre, ancrage)"
      testid="breal-biases"
      prefetch={BehavioralBiasPanel.preload}
    >
      <BehavioralBiasPanel />
    </Leaf>
    <Leaf
      title="🤐 Électeur timide (effet Bradley)"
      testid="breal-shyvoter"
      prefetch={ShyVoterPanel.preload}
    >
      <ShyVoterPanel />
    </Leaf>
    <Leaf
      title="🤯 Surcharge de choix"
      testid="breal-overload"
      prefetch={ChoiceOverloadPanel.preload}
    >
      <ChoiceOverloadPanel />
    </Leaf>
    <Leaf
      title="🗳️ Vote obligatoire"
      testid="breal-compulsory"
      prefetch={CompulsoryVotingPanel.preload}
    >
      <CompulsoryVotingPanel />
    </Leaf>
    <Leaf
      title="👥 Participation par démographie"
      testid="breal-demographic"
      prefetch={DemographicTurnoutPanel.preload}
    >
      <DemographicTurnoutPanel />
    </Leaf>
    <Leaf
      title="🔥 Polarisation affective"
      testid="breal-affective"
      prefetch={AffectivePolarizationPanel.preload}
    >
      <AffectivePolarizationPanel />
    </Leaf>
  </div>
);

export default BehavioralRealismAnchor;
