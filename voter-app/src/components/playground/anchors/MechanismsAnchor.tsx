import React from 'react';
import Leaf from './Leaf';
import { useElection } from '../../../stores/useElectionStore';

// MechanismsAnchor — the "Mécanismes alternatifs" Lab family, re-homed in the
// leader canvas: these are other ways to designate a single outcome (jury,
// sortition, delegation, deliberation…) — the leader question by another route.
// Each reads the shared electorate; lazy + Collapsible-gated.

const JuryTheoremPanel = React.lazy(() => import('../../shared/JuryTheoremPanel'));
const NOTAPanel = React.lazy(() => import('../../shared/NOTAPanel'));
const LiquidDemocracyPanel = React.lazy(() => import('../../shared/LiquidDemocracyPanel'));
const SortitionPanel = React.lazy(() => import('../../shared/SortitionPanel'));
const DeliberationPanel = React.lazy(() => import('../../shared/DeliberationPanel'));
const ConvictionVotingPanel = React.lazy(() => import('../../shared/ConvictionVotingPanel'));
const AdaptiveVotingPanel = React.lazy(() => import('../../shared/AdaptiveVotingPanel'));
const PrimarySimulator = React.lazy(() => import('../../shared/PrimarySimulator'));
const HistoricalReplay = React.lazy(() => import('../../shared/HistoricalReplay'));
const EpistocracyPanel = React.lazy(() => import('../../shared/EpistocracyPanel'));
const IdentityVotingPanel = React.lazy(() => import('../../shared/IdentityVotingPanel'));

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
      <Leaf title="⚖️ Théorème du jury (Condorcet)" testid="mech-jury">
        <JuryTheoremPanel />
      </Leaf>
      <Leaf title="🚫 Vote NOTA (aucun des candidats)" testid="mech-nota">
        <NOTAPanel />
      </Leaf>
      <Leaf title="💧 Démocratie liquide (délégation)" testid="mech-liquid">
        <LiquidDemocracyPanel />
      </Leaf>
      <Leaf title="🎲 Sortition (tirage au sort)" testid="mech-sortition">
        <SortitionPanel />
      </Leaf>
      <Leaf title="🗣️ Délibération puis vote" testid="mech-deliberation">
        <DeliberationPanel />
      </Leaf>
      <Leaf title="🪙 Vote par conviction" testid="mech-conviction">
        <ConvictionVotingPanel />
      </Leaf>
      <Leaf title="⚙️ Vote adaptatif (tactique sur durée)" testid="mech-adaptive">
        <AdaptiveVotingPanel />
      </Leaf>
      <Leaf title="🥇 Primaires" testid="mech-primary">
        <PrimarySimulator />
      </Leaf>
      <Leaf title="🕰️ Rejeu historique" testid="mech-replay">
        <HistoricalReplay />
      </Leaf>
      <Leaf title="🎓 Épistocratie (vote pondéré par compétence)" testid="mech-epistocracy">
        <EpistocracyPanel {...lab} />
      </Leaf>
      <Leaf title="🪪 Vote identitaire" testid="mech-identity">
        <IdentityVotingPanel {...lab} />
      </Leaf>
    </div>
  );
};

export default MechanismsAnchor;
