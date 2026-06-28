import React from 'react';
import { useTranslation } from 'react-i18next';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';
import { useElection } from '../../../stores/useElectionStore';

// AnalysisAnchor — the "Analyse comparative" Lab family, re-homed as a full-width
// drawer below the grid (its charts need room the narrow Bilan column lacks). It
// deepens the scorecard: distributions, regret, manipulability, collective will,
// all on the current shared electorate. Lazy + Collapsible-gated.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk (these panels pull in Recharts) before the click.

const MonteCarloResults = lazyWithPreload(() => import('../../Simulation/MonteCarloResults'));
const ManipulabilityChart = lazyWithPreload(() => import('../../Simulation/ManipulabilityChart'));
const ManipulationAnalysisPanel = lazyWithPreload(
  () => import('../../shared/ManipulationAnalysisPanel')
);
const CollectiveWillPanel = lazyWithPreload(() => import('../../shared/CollectiveWillPanel'));
const AssumptionTesterPanel = lazyWithPreload(() => import('../../shared/AssumptionTesterPanel'));
const CombinedEffectsMatrix = lazyWithPreload(() => import('../../shared/CombinedEffectsMatrix'));

const AnalysisAnchor: React.FC = () => {
  const { t } = useTranslation('playground');
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
      <p className="text-[0.7rem] text-muted-foreground/80">{t('anchorBody.analysis.intro')}</p>
      <Leaf
        title={t('anchorBody.analysis.montecarlo')}
        testid="ana-montecarlo"
        prefetch={MonteCarloResults.preload}
      >
        <MonteCarloResults baseParams={baseParams} />
      </Leaf>
      <Leaf
        title={t('anchorBody.analysis.manipulability')}
        testid="ana-manipulability"
        prefetch={ManipulabilityChart.preload}
      >
        <ManipulabilityChart baseParams={baseParams} />
      </Leaf>
      <Leaf
        title={t('anchorBody.analysis.manipulation')}
        testid="ana-manipulation"
        prefetch={ManipulationAnalysisPanel.preload}
      >
        <ManipulationAnalysisPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.analysis.collective')}
        testid="ana-collective"
        prefetch={CollectiveWillPanel.preload}
      >
        <CollectiveWillPanel {...lab} />
      </Leaf>
      <Leaf
        title={t('anchorBody.analysis.assumptions')}
        testid="ana-assumptions"
        prefetch={AssumptionTesterPanel.preload}
      >
        <AssumptionTesterPanel {...lab} />
      </Leaf>
      <Leaf
        title={t('anchorBody.analysis.combined')}
        testid="ana-combined"
        prefetch={CombinedEffectsMatrix.preload}
      >
        <CombinedEffectsMatrix />
      </Leaf>
    </div>
  );
};

export default AnalysisAnchor;
