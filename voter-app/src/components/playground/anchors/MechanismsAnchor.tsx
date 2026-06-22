import React from 'react';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';
import { useElection } from '../../../stores/useElectionStore';

// MechanismsAnchor — the "Mécanismes alternatifs" Lab family, re-homed in the
// leader canvas: these are other ways to designate a single outcome (jury,
// sortition, delegation, deliberation…) — the leader question by another route.
// Each reads the shared electorate; lazy + Collapsible-gated.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const JuryTheoremPanel = lazyWithPreload(() => import('../../shared/JuryTheoremPanel'));
const NOTAPanel = lazyWithPreload(() => import('../../shared/NOTAPanel'));
const LiquidDemocracyPanel = lazyWithPreload(() => import('../../shared/LiquidDemocracyPanel'));
const SortitionPanel = lazyWithPreload(() => import('../../shared/SortitionPanel'));
const DeliberationPanel = lazyWithPreload(() => import('../../shared/DeliberationPanel'));
const ConvictionVotingPanel = lazyWithPreload(() => import('../../shared/ConvictionVotingPanel'));
const AdaptiveVotingPanel = lazyWithPreload(() => import('../../shared/AdaptiveVotingPanel'));
const PrimarySimulator = lazyWithPreload(() => import('../../shared/PrimarySimulator'));
const HistoricalReplay = lazyWithPreload(() => import('../../shared/HistoricalReplay'));
const EpistocracyPanel = lazyWithPreload(() => import('../../shared/EpistocracyPanel'));
const IdentityVotingPanel = lazyWithPreload(() => import('../../shared/IdentityVotingPanel'));

const MechanismsAnchor: React.FC = () => {
  // Epistocracy + Identity read the shared electorate (labMode), like the Lab did.
  const { config } = useElection();
  const lab = {
    labMode: true as const,
    labCandidates: config.candidates,
    labNumVoters: config.num_voters,
    labSeed: config.seed,
  };
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">
        D’autres <strong>mécanismes</strong> de décision collective que l’élection classique —
        chacun sur le même électorat, calculé à la demande.
      </p>
      <Leaf
        title="⚖️ Théorème du jury (Condorcet)"
        testid="mech-jury"
        prefetch={JuryTheoremPanel.preload}
      >
        <JuryTheoremPanel />
      </Leaf>
      <Leaf
        title="🚫 Vote NOTA (aucun des candidats)"
        testid="mech-nota"
        prefetch={NOTAPanel.preload}
      >
        <NOTAPanel />
      </Leaf>
      <Leaf
        title="💧 Démocratie liquide (délégation)"
        testid="mech-liquid"
        prefetch={LiquidDemocracyPanel.preload}
      >
        <LiquidDemocracyPanel />
      </Leaf>
      <Leaf
        title="🎲 Sortition (tirage au sort)"
        testid="mech-sortition"
        prefetch={SortitionPanel.preload}
      >
        <SortitionPanel />
      </Leaf>
      <Leaf
        title="🗣️ Délibération puis vote"
        testid="mech-deliberation"
        prefetch={DeliberationPanel.preload}
      >
        <DeliberationPanel />
      </Leaf>
      <Leaf
        title="🪙 Vote par conviction"
        testid="mech-conviction"
        prefetch={ConvictionVotingPanel.preload}
      >
        <ConvictionVotingPanel />
      </Leaf>
      <Leaf
        title="⚙️ Vote adaptatif (tactique sur durée)"
        testid="mech-adaptive"
        prefetch={AdaptiveVotingPanel.preload}
      >
        <AdaptiveVotingPanel />
      </Leaf>
      <Leaf title="🥇 Primaires" testid="mech-primary" prefetch={PrimarySimulator.preload}>
        <PrimarySimulator />
      </Leaf>
      <Leaf title="🕰️ Rejeu historique" testid="mech-replay" prefetch={HistoricalReplay.preload}>
        <HistoricalReplay />
      </Leaf>
      <Leaf
        title="🎓 Épistocratie (vote pondéré par compétence)"
        testid="mech-epistocracy"
        prefetch={EpistocracyPanel.preload}
      >
        <EpistocracyPanel {...lab} />
      </Leaf>
      <Leaf
        title="🪪 Vote identitaire"
        testid="mech-identity"
        prefetch={IdentityVotingPanel.preload}
      >
        <IdentityVotingPanel {...lab} />
      </Leaf>
    </div>
  );
};

export default MechanismsAnchor;
