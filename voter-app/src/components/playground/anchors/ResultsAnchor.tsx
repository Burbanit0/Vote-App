import React from 'react';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';
import { useElection } from '../../../stores/useElectionStore';

// ResultsAnchor — the "Résultats & dépouillement" Lab family: the raw outcome of
// the election on the shared electorate (every method's table + the animated
// count). Re-homed full-width below the canvas, relevant in both modes. Lazy +
// Collapsible-gated.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const FullResultsModule = lazyWithPreload(() => import('../FullResultsModule'));
const VoteStepAnimator = lazyWithPreload(() => import('../../Simulation/VoteStepAnimator'));

const ResultsAnchor: React.FC = () => {
  const { config } = useElection();
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">
        Le résultat « brut » de l’élection sur l’électorat partagé : la table de toutes les méthodes
        et le dépouillement animé.
      </p>
      <Leaf
        title="📋 Résultats complets (toutes méthodes)"
        testid="res-table"
        prefetch={FullResultsModule.preload}
      >
        <FullResultsModule />
      </Leaf>
      <Leaf
        title="🎬 Dépouillement animé"
        testid="res-animation"
        prefetch={VoteStepAnimator.preload}
      >
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

export default ResultsAnchor;
