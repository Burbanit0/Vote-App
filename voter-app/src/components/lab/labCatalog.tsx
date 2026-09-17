import React from 'react';
import { lazyWithPreload } from '../lazyWithPreload';
import { useInstrumentCtx, useStoreCtx } from '../playground/PlaygroundController';
import { useElection } from '../../stores/useElectionStore';

// labCatalog — the Laboratoire's entire content as DATA. One entry per
// experiment: 53 former anchor leaves + the strategy panel split into its four
// modules + ballot + values + the methods duel, matrix and gallery = 62 fiches,
// plus thy-arrow (Arrow's impossibility theorem), restored after an unrelated
// route consolidation orphaned it (see labCatalog.test.ts's RESTORED comment)
// = 63 fiches.
// The page (LaboratoirePage) is a thin reader: a family rail, a catalogue of
// chips, and one full-width bench ("établi") that renders the selected entry —
// so no experiment ever stacks under another and nothing mounts unpicked.
//
// Ids keep the old Leaf testids verbatim: they are stable, greppable, and the
// catalog integrity test uses them to PROVE the redesign lost no content.
//
// Perf contract (unchanged from the anchors): every heavy panel is
// lazyWithPreload'd; `preload` fires on chip hover so the chunk is warm before
// the click; nothing mounts until it is on the bench.

// ── Lazy panels (formerly spread across 8 anchor files) ─────────────────────

const MethodDuel = lazyWithPreload(() => import('./MethodDuel'));
const MethodsMatrix = lazyWithPreload(() => import('./MethodsMatrix'));
const MethodGallery = lazyWithPreload(() => import('./MethodGallery'));

// Bulletin, stratégie & valeurs
const BallotConfigPanel = lazyWithPreload(() => import('../playground/BallotConfigPanel'));
const ValuesLabPanel = lazyWithPreload(() => import('../playground/ValuesLabPanel'));
const SincerityModule = lazyWithPreload(() => import('../playground/SincerityModule'));
const StrategicModule = lazyWithPreload(() => import('../playground/StrategicModule'));
const EquilibriumModule = lazyWithPreload(() => import('../playground/EquilibriumModule'));
const VseModule = lazyWithPreload(() => import('../playground/VseModule'));
const AbstentionPanel = lazyWithPreload(() => import('../shared/blank/AbstentionPanel'));

// Mécanismes alternatifs
const JuryTheoremPanel = lazyWithPreload(() => import('../shared/mechanisms/JuryTheoremPanel'));
const NOTAPanel = lazyWithPreload(() => import('../shared/blank/NOTAPanel'));
const LiquidDemocracyPanel = lazyWithPreload(
  () => import('../shared/mechanisms/LiquidDemocracyPanel')
);
const SortitionPanel = lazyWithPreload(() => import('../shared/mechanisms/SortitionPanel'));
const DeliberationPanel = lazyWithPreload(() => import('../shared/mechanisms/DeliberationPanel'));
const ConvictionVotingPanel = lazyWithPreload(
  () => import('../shared/mechanisms/ConvictionVotingPanel')
);
const EpistocracyPanel = lazyWithPreload(() => import('../shared/mechanisms/EpistocracyPanel'));
const IdentityVotingPanel = lazyWithPreload(
  () => import('../shared/mechanisms/IdentityVotingPanel')
);

// Systèmes électoraux
const CoalitionPanel = lazyWithPreload(() => import('../shared/systems/CoalitionPanel'));
const MultiwinnerCompare = lazyWithPreload(() => import('../shared/systems/MultiwinnerCompare'));
const DistrictMap = lazyWithPreload(() => import('../shared/systems/DistrictMap'));
const GerrymanderMap = lazyWithPreload(() => import('../shared/systems/GerrymanderMap'));
const STVPanel = lazyWithPreload(() => import('../shared/systems/STVPanel'));
const BallotComplexityPanel = lazyWithPreload(
  () => import('../shared/systems/BallotComplexityPanel')
);
const ElectionPipelineAnimator = lazyWithPreload(
  () => import('../shared/systems/ElectionPipelineAnimator')
);

// Trajectoires de campagne
const HotellingPanel = lazyWithPreload(() => import('../shared/campaign/HotellingPanel'));
const CampaignSensitivityPanel = lazyWithPreload(
  () => import('../shared/campaign/CampaignSensitivityPanel')
);
const PolarizationPanel = lazyWithPreload(() => import('../shared/campaign/PolarizationPanel'));
const PartyDynamicsPanel = lazyWithPreload(() => import('../shared/campaign/PartyDynamicsPanel'));

// Mécanismes temporels
const AdaptiveVotingPanel = lazyWithPreload(() => import('../shared/temporal/AdaptiveVotingPanel'));
const HistoricalReplay = lazyWithPreload(() => import('../shared/temporal/HistoricalReplay'));
const PrimarySimulator = lazyWithPreload(() => import('../shared/temporal/PrimarySimulator'));
const CascadePanel = lazyWithPreload(() => import('../shared/temporal/CascadePanel'));
const ElectoralFatiguePanel = lazyWithPreload(
  () => import('../shared/temporal/ElectoralFatiguePanel')
);

// Réalisme comportemental
const BehavioralBiasPanel = lazyWithPreload(
  () => import('../shared/behavioral/BehavioralBiasPanel')
);
const ShyVoterPanel = lazyWithPreload(() => import('../shared/behavioral/ShyVoterPanel'));
const ChoiceOverloadPanel = lazyWithPreload(
  () => import('../shared/behavioral/ChoiceOverloadPanel')
);
const CompulsoryVotingPanel = lazyWithPreload(
  () => import('../shared/behavioral/CompulsoryVotingPanel')
);
const DemographicTurnoutPanel = lazyWithPreload(
  () => import('../shared/behavioral/DemographicTurnoutPanel')
);
const AffectivePolarizationPanel = lazyWithPreload(
  () => import('../shared/behavioral/AffectivePolarizationPanel')
);

// Théorie & paradoxes
const ArrowExplorer = lazyWithPreload(() => import('../shared/theory/ArrowExplorer'));
const SenParadoxPanel = lazyWithPreload(() => import('../shared/theory/SenParadoxPanel'));
const JudgmentAggregationPanel = lazyWithPreload(
  () => import('../shared/theory/JudgmentAggregationPanel')
);
const AgendaManipulationPanel = lazyWithPreload(
  () => import('../shared/theory/AgendaManipulationPanel')
);
const MajorityTyrannyPanel = lazyWithPreload(() => import('../shared/theory/MajorityTyrannyPanel'));
const ApportionmentPanel = lazyWithPreload(() => import('../shared/theory/ApportionmentPanel'));
const PowerIndicesPanel = lazyWithPreload(() => import('../shared/theory/PowerIndicesPanel'));
const DemocraticBackslidingPanel = lazyWithPreload(
  () => import('../shared/theory/DemocraticBackslidingPanel')
);
const IntergenerationalPanel = lazyWithPreload(
  () => import('../shared/theory/IntergenerationalPanel')
);
const PolisPanel = lazyWithPreload(() => import('../shared/theory/PolisPanel'));

// Analyse approfondie
const MonteCarloResults = lazyWithPreload(() => import('../Simulation/MonteCarloResults'));
const ManipulabilityChart = lazyWithPreload(() => import('../Simulation/ManipulabilityChart'));
const ManipulationAnalysisPanel = lazyWithPreload(
  () => import('../shared/analysis/ManipulationAnalysisPanel')
);
const CollectiveWillPanel = lazyWithPreload(() => import('../shared/analysis/CollectiveWillPanel'));
const AssumptionTesterPanel = lazyWithPreload(
  () => import('../shared/analysis/AssumptionTesterPanel')
);
const CombinedEffectsMatrix = lazyWithPreload(
  () => import('../shared/analysis/CombinedEffectsMatrix')
);

// Résultats
const FullResultsModule = lazyWithPreload(() => import('../playground/FullResultsModule'));
const VoteStepAnimator = lazyWithPreload(() => import('../Simulation/VoteStepAnimator'));
const RealElectionPanel = lazyWithPreload(() => import('../playground/RealElectionPanel'));
const LexiquePanel = lazyWithPreload(() => import('./LexiquePanel'));
const BlankVotePanel = lazyWithPreload(() => import('./BlankVotePanel'));
const BlankVoteDivergencePanel = lazyWithPreload(
  () => import('../shared/blank/BlankVoteDivergencePanel')
);
const RegimeGlobe = lazyWithPreload(() => import('./RegimeGlobe'));

// ── Wrappers for panels that read the shared electorate through props ───────
// (Everything else takes no props and reads the shared state itself.)

const useLabProps = () => {
  const { config } = useElection();
  return {
    candidates: config.candidates,
    numVoters: config.num_voters,
    seed: config.seed,
    ideology: config.ideology,
  };
};
const useBaseParams = () => {
  const { config } = useElection();
  return {
    num_candidates: config.candidates.length,
    candidates: config.candidates.map((c) => c.name),
    num_voters: config.num_voters,
    ideology_distribution: config.ideology,
    seed: config.seed,
  };
};

const EpistocracyBody: React.FC = () => <EpistocracyPanel {...useLabProps()} />;
const IdentityBody: React.FC = () => <IdentityVotingPanel {...useLabProps()} />;
const MonteCarloBody: React.FC = () => <MonteCarloResults baseParams={useBaseParams()} />;
const ManipulabilityBody: React.FC = () => <ManipulabilityChart baseParams={useBaseParams()} />;
const CollectiveBody: React.FC = () => <CollectiveWillPanel {...useLabProps()} />;
const AssumptionsBody: React.FC = () => <AssumptionTesterPanel {...useLabProps()} />;
const AnimatorBody: React.FC = () => {
  const { config } = useElection();
  return (
    <VoteStepAnimator
      defaultCandidates={config.candidates.map((c) => c.name)}
      candidateConfigs={config.candidates}
      numVoters={config.num_voters}
      ideology={config.ideology}
      seed={config.seed}
    />
  );
};
const SincerityBody: React.FC = () => {
  const { votingVoters, leaderCandidates, youPos, setYouPos } = useInstrumentCtx();
  const { dims } = useStoreCtx();
  return (
    <SincerityModule
      voters={votingVoters}
      candidates={leaderCandidates}
      dims={dims}
      you={youPos}
      onYouChange={setYouPos}
    />
  );
};
const StrategicBody: React.FC = () => {
  const { config, playground } = useStoreCtx();
  return <StrategicModule config={config} playground={playground} />;
};
const EquilibriumBody: React.FC = () => {
  const { votingVoters, leaderCandidates } = useInstrumentCtx();
  return <EquilibriumModule voters={votingVoters} candidates={leaderCandidates} />;
};
const VseBody: React.FC = () => {
  const { sampleAtSeed, baseSeed, leaderCandidates } = useInstrumentCtx();
  return (
    <VseModule sampleAtSeed={sampleAtSeed} baseSeed={baseSeed} candidates={leaderCandidates} />
  );
};

// ── The catalog ──────────────────────────────────────────────────────────────

export type FamilyId = 'methods' | 'rules' | 'systems' | 'dynamics' | 'theory' | 'blank';

export interface LabExperiment {
  /** Stable id — the former Leaf testid, kept verbatim. Also the ?exp= value. */
  id: string;
  /** i18n key for the fiche/chip title (playground namespace). */
  titleKey: string;
  Body: React.ComponentType;
  /** Warms the panel's chunk on chip hover. */
  preload: () => void;
  /** The panel renders its own full header (matrix, gallery) — the bench then
   *  shows only the kicker + actions instead of doubling the title. */
  ownHeader?: boolean;
}

export interface LabGroup {
  key: string;
  /** i18n keys: the former section title/subtitle — the taxonomy, preserved. */
  titleKey: string;
  subtitleKey?: string;
  /** The former anchor intro, shown on the bench when one of its fiches is up. */
  introKey?: string;
  experiments: LabExperiment[];
}

export interface LabFamily {
  id: FamilyId;
  n: string;
  labelKey: string;
  groups: LabGroup[];
}

const exp = (
  id: string,
  titleKey: string,
  Body: React.ComponentType,
  preload: () => unknown
): LabExperiment => ({ id, titleKey, Body, preload });

export const LAB_FAMILIES: LabFamily[] = [
  {
    id: 'methods',
    n: '1',
    labelKey: 'lab.groups.methods',
    groups: [
      {
        key: 'methods',
        titleKey: 'lab.matrix.title',
        experiments: [
          {
            ...exp('lab-duel', 'duel.title', MethodDuel, MethodDuel.preload),
            ownHeader: true,
          },
          {
            ...exp('lab-matrix', 'lab.matrix.title', MethodsMatrix, MethodsMatrix.preload),
            ownHeader: true,
          },
          {
            ...exp('lab-gallery', 'gallery.title', MethodGallery, MethodGallery.preload),
            ownHeader: true,
          },
        ],
      },
    ],
  },
  {
    id: 'rules',
    n: '2',
    labelKey: 'lab.groups.rules',
    groups: [
      {
        key: 'ballot',
        titleKey: 'lab.ballot.title',
        subtitleKey: 'lab.ballot.subtitle',
        experiments: [
          exp('lab-ballot', 'lab.ballot.title', BallotConfigPanel, BallotConfigPanel.preload),
        ],
      },
      {
        key: 'strategy',
        titleKey: 'lab.strategy.title',
        subtitleKey: 'lab.strategy.subtitle',
        experiments: [
          exp('strat-sincerity', 'strategy.sincereTitle', SincerityBody, SincerityModule.preload),
          exp('strat-vuln', 'strategy.vulnTitle', StrategicBody, StrategicModule.preload),
          exp(
            'strat-equilibrium',
            'strategy.equilibriumTitle',
            EquilibriumBody,
            EquilibriumModule.preload
          ),
          exp('anchor-vse', 'vse.title', VseBody, VseModule.preload),
        ],
      },
      {
        key: 'values',
        titleKey: 'lab.values.title',
        subtitleKey: 'lab.values.subtitle',
        experiments: [
          exp('lab-values', 'lab.values.title', ValuesLabPanel, ValuesLabPanel.preload),
        ],
      },
    ],
  },
  {
    id: 'systems',
    n: '3',
    labelKey: 'lab.groups.systems',
    groups: [
      {
        key: 'mechanisms',
        titleKey: 'lab.mechanisms.title',
        subtitleKey: 'lab.mechanisms.subtitle',
        introKey: 'anchorBody.mechanisms.intro',
        experiments: [
          exp(
            'mech-jury',
            'anchorBody.mechanisms.jury',
            JuryTheoremPanel,
            JuryTheoremPanel.preload
          ),
          exp(
            'mech-liquid',
            'anchorBody.mechanisms.liquid',
            LiquidDemocracyPanel,
            LiquidDemocracyPanel.preload
          ),
          exp(
            'mech-sortition',
            'anchorBody.mechanisms.sortition',
            SortitionPanel,
            SortitionPanel.preload
          ),
          exp(
            'mech-deliberation',
            'anchorBody.mechanisms.deliberation',
            DeliberationPanel,
            DeliberationPanel.preload
          ),
          exp(
            'mech-conviction',
            'anchorBody.mechanisms.conviction',
            ConvictionVotingPanel,
            ConvictionVotingPanel.preload
          ),
          exp(
            'mech-epistocracy',
            'anchorBody.mechanisms.epistocracy',
            EpistocracyBody,
            EpistocracyPanel.preload
          ),
          exp(
            'mech-identity',
            'anchorBody.mechanisms.identity',
            IdentityBody,
            IdentityVotingPanel.preload
          ),
        ],
      },
      {
        key: 'systems',
        titleKey: 'lab.systems.title',
        subtitleKey: 'lab.systems.subtitle',
        introKey: 'anchorBody.systems.intro',
        experiments: [
          exp(
            'sys-coalition',
            'anchorBody.systems.coalition',
            CoalitionPanel,
            CoalitionPanel.preload
          ),
          exp(
            'sys-multiwinner',
            'anchorBody.systems.multiwinner',
            MultiwinnerCompare,
            MultiwinnerCompare.preload
          ),
          exp('sys-districts', 'anchorBody.systems.districts', DistrictMap, DistrictMap.preload),
          exp(
            'sys-gerrymander',
            'anchorBody.systems.gerrymander',
            GerrymanderMap,
            GerrymanderMap.preload
          ),
          exp('sys-stv', 'anchorBody.systems.stv', STVPanel, STVPanel.preload),
          exp(
            'sys-ballot',
            'anchorBody.systems.ballot',
            BallotComplexityPanel,
            BallotComplexityPanel.preload
          ),
          exp(
            'sys-pipeline',
            'anchorBody.systems.pipeline',
            ElectionPipelineAnimator,
            ElectionPipelineAnimator.preload
          ),
          exp('sys-atlas', 'atlas.title', RegimeGlobe, RegimeGlobe.preload),
        ],
      },
    ],
  },
  {
    id: 'dynamics',
    n: '4',
    labelKey: 'lab.groups.dynamics',
    groups: [
      {
        key: 'campaign',
        titleKey: 'lab.campaign.title',
        subtitleKey: 'lab.campaign.subtitle',
        introKey: 'anchorBody.campaign.intro',
        experiments: [
          exp(
            'dyn-hotelling',
            'anchorBody.campaign.hotelling',
            HotellingPanel,
            HotellingPanel.preload
          ),
          exp(
            'dyn-campaign',
            'anchorBody.campaign.campaign',
            CampaignSensitivityPanel,
            CampaignSensitivityPanel.preload
          ),
          exp(
            'dyn-polarization',
            'anchorBody.campaign.polarization',
            PolarizationPanel,
            PolarizationPanel.preload
          ),
          exp(
            'dyn-party',
            'anchorBody.campaign.party',
            PartyDynamicsPanel,
            PartyDynamicsPanel.preload
          ),
        ],
      },
      {
        key: 'temporal',
        titleKey: 'lab.temporal.title',
        subtitleKey: 'lab.temporal.subtitle',
        introKey: 'anchorBody.tdyn.intro',
        experiments: [
          exp(
            'tdyn-adaptive',
            'anchorBody.tdyn.adaptive',
            AdaptiveVotingPanel,
            AdaptiveVotingPanel.preload
          ),
          exp('tdyn-replay', 'anchorBody.tdyn.replay', HistoricalReplay, HistoricalReplay.preload),
          exp(
            'tdyn-primary',
            'anchorBody.tdyn.primary',
            PrimarySimulator,
            PrimarySimulator.preload
          ),
          exp('tdyn-cascade', 'anchorBody.tdyn.cascade', CascadePanel, CascadePanel.preload),
          exp(
            'tdyn-fatigue',
            'anchorBody.tdyn.fatigue',
            ElectoralFatiguePanel,
            ElectoralFatiguePanel.preload
          ),
        ],
      },
      {
        key: 'behavioral',
        titleKey: 'lab.behavioral.title',
        subtitleKey: 'lab.behavioral.subtitle',
        introKey: 'anchorBody.breal.intro',
        experiments: [
          exp(
            'breal-biases',
            'anchorBody.breal.biases',
            BehavioralBiasPanel,
            BehavioralBiasPanel.preload
          ),
          exp('breal-shyvoter', 'anchorBody.breal.shyvoter', ShyVoterPanel, ShyVoterPanel.preload),
          exp(
            'breal-overload',
            'anchorBody.breal.overload',
            ChoiceOverloadPanel,
            ChoiceOverloadPanel.preload
          ),
          exp(
            'breal-compulsory',
            'anchorBody.breal.compulsory',
            CompulsoryVotingPanel,
            CompulsoryVotingPanel.preload
          ),
          exp(
            'breal-demographic',
            'anchorBody.breal.demographic',
            DemographicTurnoutPanel,
            DemographicTurnoutPanel.preload
          ),
          exp(
            'breal-affective',
            'anchorBody.breal.affective',
            AffectivePolarizationPanel,
            AffectivePolarizationPanel.preload
          ),
        ],
      },
    ],
  },
  {
    id: 'theory',
    n: '5',
    labelKey: 'lab.groups.theory',
    groups: [
      {
        key: 'theory',
        titleKey: 'lab.theory.title',
        subtitleKey: 'lab.theory.subtitle',
        introKey: 'anchorBody.theory.intro',
        experiments: [
          exp('lexique', 'lexique.title', LexiquePanel, LexiquePanel.preload),
          exp('thy-arrow', 'anchorBody.theory.arrow', ArrowExplorer, ArrowExplorer.preload),
          exp('thy-sen', 'anchorBody.theory.sen', SenParadoxPanel, SenParadoxPanel.preload),
          exp(
            'thy-judgment',
            'anchorBody.theory.judgment',
            JudgmentAggregationPanel,
            JudgmentAggregationPanel.preload
          ),
          exp(
            'thy-agenda',
            'anchorBody.theory.agenda',
            AgendaManipulationPanel,
            AgendaManipulationPanel.preload
          ),
          exp(
            'thy-tyranny',
            'anchorBody.theory.tyranny',
            MajorityTyrannyPanel,
            MajorityTyrannyPanel.preload
          ),
          exp(
            'thy-apportionment',
            'anchorBody.theory.apportionment',
            ApportionmentPanel,
            ApportionmentPanel.preload
          ),
          exp('thy-power', 'anchorBody.theory.power', PowerIndicesPanel, PowerIndicesPanel.preload),
          exp(
            'thy-backsliding',
            'anchorBody.theory.backsliding',
            DemocraticBackslidingPanel,
            DemocraticBackslidingPanel.preload
          ),
          exp(
            'thy-intergen',
            'anchorBody.theory.intergen',
            IntergenerationalPanel,
            IntergenerationalPanel.preload
          ),
          exp('thy-polis', 'anchorBody.theory.polis', PolisPanel, PolisPanel.preload),
        ],
      },
      {
        key: 'analysis',
        titleKey: 'lab.analysis.title',
        subtitleKey: 'lab.analysis.subtitle',
        introKey: 'anchorBody.analysis.intro',
        experiments: [
          exp(
            'ana-montecarlo',
            'anchorBody.analysis.montecarlo',
            MonteCarloBody,
            MonteCarloResults.preload
          ),
          exp(
            'ana-manipulability',
            'anchorBody.analysis.manipulability',
            ManipulabilityBody,
            ManipulabilityChart.preload
          ),
          exp(
            'ana-manipulation',
            'anchorBody.analysis.manipulation',
            ManipulationAnalysisPanel,
            ManipulationAnalysisPanel.preload
          ),
          exp(
            'ana-collective',
            'anchorBody.analysis.collective',
            CollectiveBody,
            CollectiveWillPanel.preload
          ),
          exp(
            'ana-assumptions',
            'anchorBody.analysis.assumptions',
            AssumptionsBody,
            AssumptionTesterPanel.preload
          ),
          exp(
            'ana-combined',
            'anchorBody.analysis.combined',
            CombinedEffectsMatrix,
            CombinedEffectsMatrix.preload
          ),
        ],
      },
      {
        key: 'results',
        titleKey: 'lab.results.title',
        subtitleKey: 'lab.results.subtitle',
        introKey: 'anchorBody.results.intro',
        experiments: [
          exp(
            'res-table',
            'anchorBody.results.table',
            FullResultsModule,
            FullResultsModule.preload
          ),
          exp(
            'res-animation',
            'anchorBody.results.animation',
            AnimatorBody,
            VoteStepAnimator.preload
          ),
          exp(
            'res-real-election',
            'realElection.title',
            RealElectionPanel,
            RealElectionPanel.preload
          ),
        ],
      },
    ],
  },
  {
    id: 'blank',
    n: '6',
    labelKey: 'lab.groups.blank',
    groups: [
      {
        key: 'blank',
        titleKey: 'lab.blank.title',
        subtitleKey: 'lab.blank.subtitle',
        introKey: 'anchorBody.blank.intro',
        experiments: [
          exp('thy-blank', 'blankVote.title', BlankVotePanel, BlankVotePanel.preload),
          exp(
            'blank-divergence',
            'method.blankAnchorTitle',
            BlankVoteDivergencePanel,
            BlankVoteDivergencePanel.preload
          ),
          exp('mech-nota', 'anchorBody.mechanisms.nota', NOTAPanel, NOTAPanel.preload),
          exp(
            'anchor-abstention',
            'electorate.abstentionAnchorTitle',
            AbstentionPanel,
            AbstentionPanel.preload
          ),
        ],
      },
    ],
  },
];

// ── Lookup helpers (the page + tests read these) ────────────────────────────

export const ALL_EXPERIMENTS: LabExperiment[] = LAB_FAMILIES.flatMap((f) =>
  f.groups.flatMap((g) => g.experiments)
);

export interface Located {
  family: LabFamily;
  group: LabGroup;
  experiment: LabExperiment;
}

export function locateExperiment(id: string): Located | null {
  for (const family of LAB_FAMILIES)
    for (const group of family.groups)
      for (const experiment of group.experiments)
        if (experiment.id === id) return { family, group, experiment };
  return null;
}

export const DEFAULT_EXPERIMENT = 'lab-matrix';
