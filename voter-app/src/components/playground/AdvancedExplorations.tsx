import React from 'react';
import Collapsible from './Collapsible';
import Leaf from './anchors/Leaf';
import { useElection } from '../../stores/useElectionStore';

// AdvancedExplorations — the Lab phenomena that have not yet been re-homed to a
// contextual anchor. Everything here is OFF the critical path:
//   · ships collapsed (Collapsible only mounts children when open → 0 compute,
//     0 network until the user asks);
//   · each panel is React.lazy (code-split out of the playground chunk);
//   · panels read the SAME shared electorate via useElection() (no new props).
// As families are re-homed next to the concept they deepen (Comportement →
// Setup rail, Dynamiques → mode campagne, …), they leave this row; the goal is
// for the catch-all to shrink to nothing.

// ── Lazy panels (Mécanismes alternatifs family) ──────────────────────────────
const JuryTheoremPanel = React.lazy(() => import('../shared/JuryTheoremPanel'));
const NOTAPanel = React.lazy(() => import('../shared/NOTAPanel'));
const LiquidDemocracyPanel = React.lazy(() => import('../shared/LiquidDemocracyPanel'));
const SortitionPanel = React.lazy(() => import('../shared/SortitionPanel'));
const DeliberationPanel = React.lazy(() => import('../shared/DeliberationPanel'));
const ConvictionVotingPanel = React.lazy(() => import('../shared/ConvictionVotingPanel'));
const AdaptiveVotingPanel = React.lazy(() => import('../shared/AdaptiveVotingPanel'));
const PrimarySimulator = React.lazy(() => import('../shared/PrimarySimulator'));
const HistoricalReplay = React.lazy(() => import('../shared/HistoricalReplay'));
const EpistocracyPanel = React.lazy(() => import('../shared/EpistocracyPanel'));
const IdentityVotingPanel = React.lazy(() => import('../shared/IdentityVotingPanel'));

// ── Lazy panels (Analyse comparative family) ─────────────────────────────────
const ManipulationAnalysisPanel = React.lazy(() => import('../shared/ManipulationAnalysisPanel'));
const ManipulabilityChart = React.lazy(() => import('../Simulation/ManipulabilityChart'));
const MonteCarloResults = React.lazy(() => import('../Simulation/MonteCarloResults'));
const CollectiveWillPanel = React.lazy(() => import('../shared/CollectiveWillPanel'));
const AssumptionTesterPanel = React.lazy(() => import('../shared/AssumptionTesterPanel'));
const CombinedEffectsMatrix = React.lazy(() => import('../shared/CombinedEffectsMatrix'));

// ── Lazy panels (Espace & dynamiques family) ─────────────────────────────────
const HotellingPanel = React.lazy(() => import('../shared/HotellingPanel'));
const PolarizationPanel = React.lazy(() => import('../shared/PolarizationPanel'));
const PartyDynamicsPanel = React.lazy(() => import('../shared/PartyDynamicsPanel'));
const CampaignSensitivityPanel = React.lazy(() => import('../shared/CampaignSensitivityPanel'));

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

const MechanismsFamily: React.FC = () => {
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

const AnalysisFamily: React.FC = () => {
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
        manipulabilité, volonté collective.
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

const DynamicsFamily: React.FC = () => (
  <div className="flex flex-col gap-2">
    <p className="text-[0.7rem] text-muted-foreground/80">
      Comment les positions et les dynamiques de campagne déplacent le résultat dans le temps.
    </p>
    <Leaf title="📐 Équilibre de Hotelling-Downs" testid="dyn-hotelling">
      <HotellingPanel />
    </Leaf>
    <Leaf title="↔️ Polarisation" testid="dyn-polarization">
      <PolarizationPanel />
    </Leaf>
    <Leaf title="🏳️ Dynamique des partis" testid="dyn-party">
      <PartyDynamicsPanel />
    </Leaf>
    <Leaf title="📣 Sensibilité de campagne" testid="dyn-campaign">
      <CampaignSensitivityPanel />
    </Leaf>
  </div>
);

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
          title="⚙️ Mécanismes alternatifs"
          subtitle="11 mécanismes"
          testid="family-mechanisms"
        >
          <MechanismsFamily />
        </Collapsible>
        <Collapsible title="📊 Analyse comparative" subtitle="6 mesures" testid="family-analysis">
          <AnalysisFamily />
        </Collapsible>
        <Collapsible title="📐 Espace & dynamiques" subtitle="4 vues" testid="family-dynamics">
          <DynamicsFamily />
        </Collapsible>
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
