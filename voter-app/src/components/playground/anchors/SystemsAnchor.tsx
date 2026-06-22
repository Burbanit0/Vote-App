import React from 'react';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';

// SystemsAnchor — the "Systèmes & circonscriptions" Lab family, re-homed in the
// parliament canvas: electoral systems and geography (seats, coalitions,
// districts, ballot, gerrymander) belong to the parliament question. Each panel
// reads the shared electorate; lazy + Collapsible-gated.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const CoalitionPanel = lazyWithPreload(() => import('../../shared/CoalitionPanel'));
const MultiwinnerCompare = lazyWithPreload(() => import('../../shared/MultiwinnerCompare'));
const DistrictMap = lazyWithPreload(() => import('../../shared/DistrictMap'));
const GerrymanderMap = lazyWithPreload(() => import('../../shared/GerrymanderMap'));
const STVPanel = lazyWithPreload(() => import('../../shared/STVPanel'));
const BallotComplexityPanel = lazyWithPreload(() => import('../../shared/BallotComplexityPanel'));
const ElectionPipelineAnimator = lazyWithPreload(
  () => import('../../shared/ElectionPipelineAnimator')
);

const SystemsAnchor: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Systèmes électoraux et géographie : sièges, coalitions, circonscriptions, bulletin. Chaque
      module se calcule à la demande.
    </p>
    <Leaf title="🤝 Coalitions" testid="sys-coalition" prefetch={CoalitionPanel.preload}>
      <CoalitionPanel />
    </Leaf>
    <Leaf
      title="🪑 Multiwinner (STV/SPAV/Phragmén)"
      testid="sys-multiwinner"
      prefetch={MultiwinnerCompare.preload}
    >
      <MultiwinnerCompare />
    </Leaf>
    <Leaf title="🗺️ Circonscriptions" testid="sys-districts" prefetch={DistrictMap.preload}>
      <DistrictMap />
    </Leaf>
    <Leaf
      title="✂️ Charcutage (gerrymander)"
      testid="sys-gerrymander"
      prefetch={GerrymanderMap.preload}
    >
      <GerrymanderMap />
    </Leaf>
    <Leaf title="🔁 Vote unique transférable (STV)" testid="sys-stv" prefetch={STVPanel.preload}>
      <STVPanel />
    </Leaf>
    <Leaf
      title="📋 Complexité du bulletin"
      testid="sys-ballot"
      prefetch={BallotComplexityPanel.preload}
    >
      <BallotComplexityPanel />
    </Leaf>
    <Leaf
      title="🎬 Pipeline d’élection (animation)"
      testid="sys-pipeline"
      prefetch={ElectionPipelineAnimator.preload}
    >
      <ElectionPipelineAnimator />
    </Leaf>
  </div>
);

export default SystemsAnchor;
