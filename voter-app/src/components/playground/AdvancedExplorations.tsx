import React from 'react';
import Collapsible from './Collapsible';

// AdvancedExplorations — the Lab phenomena absorbed into the playground without
// touching its two-mode core. Everything here is OFF the critical path:
//   · ships collapsed (Collapsible only mounts children when open → 0 compute,
//     0 network until the user asks);
//   · each panel is React.lazy (code-split out of the playground chunk);
//   · panels read the SAME shared electorate via useElection() (no new props).
// The playground's default first paint gains exactly one collapsed row.

// ── Lazy panels (Comportement family) ────────────────────────────────────────
const CascadePanel = React.lazy(() => import('../shared/CascadePanel'));
const BehavioralBiasPanel = React.lazy(() => import('../shared/BehavioralBiasPanel'));
const AffectivePolarizationPanel = React.lazy(() => import('../shared/AffectivePolarizationPanel'));
const ShyVoterPanel = React.lazy(() => import('../shared/ShyVoterPanel'));
const ElectoralFatiguePanel = React.lazy(() => import('../shared/ElectoralFatiguePanel'));
const ChoiceOverloadPanel = React.lazy(() => import('../shared/ChoiceOverloadPanel'));
const CompulsoryVotingPanel = React.lazy(() => import('../shared/CompulsoryVotingPanel'));
const DemographicTurnoutPanel = React.lazy(() => import('../shared/DemographicTurnoutPanel'));
const BlankVoteDivergencePanel = React.lazy(() => import('../shared/BlankVoteDivergencePanel'));

const Fallback: React.FC = () => <p className="p-2 text-xs text-muted-foreground">Chargement…</p>;

/** A leaf module: a collapsed sub-section that lazy-mounts its panel on open. */
const Leaf: React.FC<{ title: string; testid: string; children: React.ReactNode }> = ({
  title,
  testid,
  children,
}) => (
  <Collapsible title={title} testid={testid}>
    <React.Suspense fallback={<Fallback />}>{children}</React.Suspense>
  </Collapsible>
);

const BehaviorFamily: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Comment le <strong>comportement</strong> réel des électeurs (biais, cascades, abstention
      différentielle, fatigue…) déplace le résultat sur le même électorat. Chaque module se calcule
      à la demande.
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
    <Leaf title="⬜ Divergence du vote blanc" testid="beh-blank">
      <BlankVoteDivergencePanel />
    </Leaf>
  </div>
);

const AdvancedExplorations: React.FC = () => (
  <div className="mt-4">
    <Collapsible
      title="🔬 Explorations avancées"
      subtitle="phénomènes du Lab, sur le même électorat"
      testid="module-advanced"
    >
      <div className="flex flex-col gap-3">
        <Collapsible
          title="🧠 Comportement des électeurs"
          subtitle="9 phénomènes"
          testid="family-behavior"
        >
          <BehaviorFamily />
        </Collapsible>
      </div>
    </Collapsible>
  </div>
);

export default AdvancedExplorations;
