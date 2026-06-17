import React from 'react';
import Leaf from './Leaf';

// SystemsAnchor — the "Systèmes & circonscriptions" Lab family, re-homed in the
// parliament canvas: electoral systems and geography (seats, coalitions,
// districts, ballot, gerrymander) belong to the parliament question. Each panel
// reads the shared electorate; lazy + Collapsible-gated.

const CoalitionPanel = React.lazy(() => import('../../shared/CoalitionPanel'));
const MultiwinnerCompare = React.lazy(() => import('../../shared/MultiwinnerCompare'));
const DistrictMap = React.lazy(() => import('../../shared/DistrictMap'));
const GerrymanderMap = React.lazy(() => import('../../shared/GerrymanderMap'));
const STVPanel = React.lazy(() => import('../../shared/STVPanel'));
const BallotComplexityPanel = React.lazy(() => import('../../shared/BallotComplexityPanel'));
const ElectionPipelineAnimator = React.lazy(() => import('../../shared/ElectionPipelineAnimator'));

const SystemsAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Systèmes électoraux et géographie : sièges, coalitions, circonscriptions, bulletin. Chaque
      module se calcule à la demande.
    </p>
    <Leaf title="🤝 Coalitions" testid="sys-coalition">
      <CoalitionPanel />
    </Leaf>
    <Leaf title="🪑 Multiwinner (STV/SPAV/Phragmén)" testid="sys-multiwinner">
      <MultiwinnerCompare />
    </Leaf>
    <Leaf title="🗺️ Circonscriptions" testid="sys-districts">
      <DistrictMap />
    </Leaf>
    <Leaf title="✂️ Charcutage (gerrymander)" testid="sys-gerrymander">
      <GerrymanderMap />
    </Leaf>
    <Leaf title="🔁 Vote unique transférable (STV)" testid="sys-stv">
      <STVPanel />
    </Leaf>
    <Leaf title="📋 Complexité du bulletin" testid="sys-ballot">
      <BallotComplexityPanel />
    </Leaf>
    <Leaf title="🎬 Pipeline d’élection (animation)" testid="sys-pipeline">
      <ElectionPipelineAnimator />
    </Leaf>
  </div>
);

export default SystemsAnchor;
