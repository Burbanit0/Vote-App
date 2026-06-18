import React from 'react';
import Leaf from './Leaf';

// TheoryAnchor — the social-choice paradoxes & democratic-theory panels that
// used to live only on TheoryPage, re-homed into the playground so the single
// surface covers the whole inventory. All panels are self-contained (no props);
// lazy + Collapsible-gated, so nothing computes until a leaf is opened.

const SenParadoxPanel = React.lazy(() => import('../../shared/SenParadoxPanel'));
const JudgmentAggregationPanel = React.lazy(() => import('../../shared/JudgmentAggregationPanel'));
const AgendaManipulationPanel = React.lazy(() => import('../../shared/AgendaManipulationPanel'));
const MajorityTyrannyPanel = React.lazy(() => import('../../shared/MajorityTyrannyPanel'));
const ApportionmentPanel = React.lazy(() => import('../../shared/ApportionmentPanel'));
const PowerIndicesPanel = React.lazy(() => import('../../shared/PowerIndicesPanel'));
const DemocraticBackslidingPanel = React.lazy(
  () => import('../../shared/DemocraticBackslidingPanel')
);
const IntergenerationalPanel = React.lazy(() => import('../../shared/IntergenerationalPanel'));
const PolisPanel = React.lazy(() => import('../../shared/PolisPanel'));

const TheoryAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Les <strong>paradoxes</strong> du choix social et la théorie démocratique — les limites
      formelles que toute règle de vote doit affronter. Chaque module se calcule à la demande.
    </p>
    <Leaf title="🔓 Paradoxe de Sen (libéral parétien)" testid="thy-sen">
      <SenParadoxPanel />
    </Leaf>
    <Leaf title="🧩 Agrégation de jugements (dilemme discursif)" testid="thy-judgment">
      <JudgmentAggregationPanel />
    </Leaf>
    <Leaf title="🎚️ Manipulation d’agenda (McKelvey)" testid="thy-agenda">
      <AgendaManipulationPanel />
    </Leaf>
    <Leaf title="👥 Tyrannie de la majorité" testid="thy-tyranny">
      <MajorityTyrannyPanel />
    </Leaf>
    <Leaf title="🧮 Apportionnement (Balinski-Young)" testid="thy-apportionment">
      <ApportionmentPanel />
    </Leaf>
    <Leaf title="⚖️ Indices de pouvoir (Shapley-Shubik, Banzhaf)" testid="thy-power">
      <PowerIndicesPanel />
    </Leaf>
    <Leaf title="📉 Recul démocratique (Levitsky-Ziblatt)" testid="thy-backsliding">
      <DemocraticBackslidingPanel />
    </Leaf>
    <Leaf title="⏳ Représentation intergénérationnelle" testid="thy-intergen">
      <IntergenerationalPanel />
    </Leaf>
    <Leaf title="🗣️ Pol.is (clustering délibératif)" testid="thy-polis">
      <PolisPanel />
    </Leaf>
  </div>
);

export default TheoryAnchor;
