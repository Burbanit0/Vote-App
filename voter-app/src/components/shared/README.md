# components/shared/

Cross-cutting React components reused across multiple pages.

## Sub-folder organisation (in progress)

This directory has 70+ files at the top level. To make navigation easier
for new contributors, we are progressively moving components into
thematic sub-folders:

| Sub-folder       | What goes here                                                                                    |
|------------------|---------------------------------------------------------------------------------------------------|
| `perturbers/`    | "Perturber" tabs that apply a single effect to a baseline election (Abstention, Cascade, BehavioralBias, ChoiceOverload, ShyVoter, ElectoralFatigue, NOTA, BallotComplexity, Deliberation, CompulsoryVoting, DemographicTurnout, ManipulationAnalysis, AffectivePolarization, AdaptiveVoting, BlankVoteDivergence, CampaignSensitivity). |
| `theory/`        | Theory-page panels for paradoxes and impossibilities (MajorityTyranny, AgendaManipulation, JudgmentAggregation, SenParadox, Apportionment, IdentityVoting, Epistocracy, Intergenerational, DemocraticBacksliding, PowerIndices, CollectiveWill, AssumptionTester). |
| `electoral/`     | Electoral system variants and their visualisations (Coalition, DistrictMap, GerrymanderMap, PrimarySimulator, STV, MultiwinnerCompare, LiquidDemocracy, ConvictionVoting, Sortition, JuryTheorem, Hotelling, Polarization, PartyDynamics). |
| `ui/`            | Generic UI primitives (ToastNotification, LiveBadge, UpdatePrompt, OfflineBanner, ResponsiveTable, MetricTooltip, EmptyChart, SkeletonCard). |

## Migration status

- ⏳ `perturbers/`, `theory/`, `electoral/`, `ui/` — created (empty), file moves
  to come in follow-up PRs. Each migration is a `git mv` plus updating the
  importers (typically 1–10 sites per file).
- The Election Lab central view ecosystem this migration originally started
  with (`LabCentralView`, `LabOnboardingTour`, `ScenarioIO`) was retired
  outright, not migrated — that feature was folded into the Playground, so
  there is no `lab/` sub-folder.

## Why incremental

A "move all 70 files in one PR" change touches ~150 importers and is
unreviewable. Doing one cohesive group per PR keeps the diff focused and
makes regressions easy to bisect.
