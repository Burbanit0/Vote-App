import React from 'react';
import Leaf from './Leaf';
import { useElection } from '../../../stores/useElectionStore';

// AnalysisAnchor — the "Analyse comparative" Lab family, re-homed as a full-width
// drawer below the grid (its charts need room the narrow Bilan column lacks). It
// deepens the scorecard: distributions, regret, manipulability, collective will,
// all on the current shared electorate. Lazy + Collapsible-gated.

const MonteCarloResults = React.lazy(() => import('../../Simulation/MonteCarloResults'));
const ManipulabilityChart = React.lazy(() => import('../../Simulation/ManipulabilityChart'));
const ManipulationAnalysisPanel = React.lazy(
  () => import('../../shared/ManipulationAnalysisPanel')
);
const CollectiveWillPanel = React.lazy(() => import('../../shared/CollectiveWillPanel'));
const AssumptionTesterPanel = React.lazy(() => import('../../shared/AssumptionTesterPanel'));
const CombinedEffectsMatrix = React.lazy(() => import('../../shared/CombinedEffectsMatrix'));

const AnalysisAnchor: React.FC = () => {
  const { config } = useElection();
  const baseParams = {
    num_candidates: config.candidates.length,
    candidates: config.candidates.map((c) => c.name),
    num_voters: config.num_voters,
    ideology_distribution: config.ideology,
    seed: config.seed,
  };
  const lab = {
    labMode: true as const,
    labCandidates: config.candidates,
    labNumVoters: config.num_voters,
    labSeed: config.seed,
    labIdeology: config.ideology,
  };
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">
        Mesures comparatives approfondies sur le même électorat — distributions, regret,
        manipulabilité, volonté collective. Chaque module se calcule à la demande.
      </p>
      <Leaf title="🎲 Monte-Carlo (distributions)" testid="ana-montecarlo">
        <MonteCarloResults baseParams={baseParams} />
      </Leaf>
      <Leaf title="🕵 Manipulabilité (par méthode)" testid="ana-manipulability">
        <ManipulabilityChart baseParams={baseParams} />
      </Leaf>
      <Leaf title="🎯 Analyse de manipulation" testid="ana-manipulation">
        <ManipulationAnalysisPanel />
      </Leaf>
      <Leaf title="🤝 Volonté collective" testid="ana-collective">
        <CollectiveWillPanel {...lab} />
      </Leaf>
      <Leaf title="🧪 Test des hypothèses" testid="ana-assumptions">
        <AssumptionTesterPanel {...lab} />
      </Leaf>
      <Leaf title="🧮 Effets combinés (factoriel)" testid="ana-combined">
        <CombinedEffectsMatrix />
      </Leaf>
    </div>
  );
};

export default AnalysisAnchor;
