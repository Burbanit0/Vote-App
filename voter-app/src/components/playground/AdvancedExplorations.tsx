import React from 'react';
import Collapsible from './Collapsible';
import Leaf from './anchors/Leaf';
import { useElection } from '../../stores/useElectionStore';

// AdvancedExplorations — the last Lab families not yet re-homed to a contextual
// anchor (Systèmes → parliament, Résultats → canvas, landing in PR4). Everything
// here is OFF the critical path: ships collapsed (Collapsible only mounts its
// children when open), each panel is React.lazy, and panels read the SAME shared
// electorate via useElection(). The goal is for this catch-all to disappear.

// ── Lazy panels (Systèmes & circonscriptions family) ─────────────────────────
const CoalitionPanel = React.lazy(() => import('../shared/CoalitionPanel'));
const MultiwinnerCompare = React.lazy(() => import('../shared/MultiwinnerCompare'));
const DistrictMap = React.lazy(() => import('../shared/DistrictMap'));
const GerrymanderMap = React.lazy(() => import('../shared/GerrymanderMap'));
const STVPanel = React.lazy(() => import('../shared/STVPanel'));
const BallotComplexityPanel = React.lazy(() => import('../shared/BallotComplexityPanel'));
const ElectionPipelineAnimator = React.lazy(() => import('../shared/ElectionPipelineAnimator'));

// ── Lazy panels (Résultats & dépouillement family) ───────────────────────────
const FullResultsModule = React.lazy(() => import('./FullResultsModule'));
const VoteStepAnimator = React.lazy(() => import('../Simulation/VoteStepAnimator'));

const SystemsFamily: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Systèmes électoraux et géographie : sièges, coalitions, circonscriptions, bulletin.
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

const ResultsFamily: React.FC = () => {
  const { config } = useElection();
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">
        Le résultat « brut » de l’élection sur l’électorat partagé : la table de toutes les méthodes
        et le dépouillement animé.
      </p>
      <Leaf title="📋 Résultats complets (toutes méthodes)" testid="res-table">
        <FullResultsModule />
      </Leaf>
      <Leaf title="🎬 Dépouillement animé" testid="res-animation">
        <VoteStepAnimator
          defaultCandidates={config.candidates.map((c) => c.name)}
          candidateConfigs={config.candidates}
          numVoters={config.num_voters}
          ideology={config.ideology}
          seed={config.seed}
        />
      </Leaf>
    </div>
  );
};

const AdvancedExplorations: React.FC = () => (
  <div className="mt-4">
    <Collapsible
      title="🔬 Explorations avancées"
      subtitle="phénomènes du Lab, sur le même électorat"
      testid="module-advanced"
    >
      <div className="flex flex-col gap-3">
        <Collapsible
          title="🏛️ Systèmes & circonscriptions"
          subtitle="7 vues"
          testid="family-systems"
        >
          <SystemsFamily />
        </Collapsible>
        <Collapsible
          title="📋 Résultats & dépouillement"
          subtitle="table + animation"
          testid="family-results"
        >
          <ResultsFamily />
        </Collapsible>
      </div>
    </Collapsible>
  </div>
);

export default AdvancedExplorations;
