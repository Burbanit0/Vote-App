# components/shared/

Cross-cutting React components reused across multiple pages, organised into
thematic sub-folders (2026-09-12 — see `CODE_AUDIT.md` §6/§7 for the "flat
directory" finding this closes).

Most files here are Laboratoire "fiches" (paradox/mechanism/theory panels),
one per experiment in `../lab/labCatalog.tsx` — the Laboratoire's own,
tested catalogue of what each panel covers. The sub-folders below mirror
that catalogue's grouping rather than inventing a new taxonomy: a panel
lives where `labCatalog.tsx` already classifies it, based on what it
actually renders (its content, imports and i18n keys), not on its filename.

| Sub-folder    | What goes here                                                                                                                                                                             |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `mechanisms/` | Alternative governance mechanisms (JuryTheorem, LiquidDemocracy, Sortition, Deliberation, ConvictionVoting, Epistocracy, IdentityVoting).                                                  |
| `systems/`    | Electoral systems and their visualisations (Coalition, MultiwinnerCompare, DistrictMap, GerrymanderMap, STV, BallotComplexity, ElectionPipelineAnimator, HemicycleLegend).                 |
| `campaign/`   | Campaign & spatial dynamics (Hotelling, CampaignSensitivity + its CampaignSwimlane helper, Polarization, PartyDynamics).                                                                   |
| `temporal/`   | Temporal/strategic mechanisms (AdaptiveVoting, HistoricalReplay, PrimarySimulator, Cascade, ElectoralFatigue).                                                                             |
| `behavioral/` | Behavioural & psychological effects (BehavioralBias, ShyVoter, ChoiceOverload, CompulsoryVoting, DemographicTurnout, AffectivePolarization).                                               |
| `theory/`     | Paradoxes and impossibility theorems (SenParadox, JudgmentAggregation, AgendaManipulation, MajorityTyranny, Apportionment, PowerIndices, DemocraticBacksliding, Intergenerational, Polis). |
| `analysis/`   | Deep/meta-analysis panels (ManipulationAnalysis, CollectiveWill, AssumptionTester, CombinedEffectsMatrix).                                                                                 |
| `blank/`      | The blank-vote / none-of-the-above family (NOTA, BlankVoteDivergence, Abstention).                                                                                                         |
| `results/`    | Results-reporting helpers consumed by `playground/FullResultsModule` (ElectionInsightPanel, HistoricalReferencePanel, ResultsMethodTable, MethodGroupDonut).                               |
| `ui/`         | Generic, app-wide UI primitives (LiveBadge, UpdatePrompt, OfflineBanner, ResponsiveTable, MetricTooltip, SkeletonCard).                                                                    |
| `common/`     | Genuinely cross-cutting, non-panel, non-primitive components used in exactly one page each and not fitting the panel taxonomy (CuriosityQuestions, OnboardingTour).                        |

Each sub-folder has its own `__tests__/`, matching the convention already
used elsewhere in `components/` (`playground/__tests__/`, `lab/__tests__/`,
`Simulation/__tests__/`, etc.) rather than one flat `shared/__tests__/`.

## History

- 2026-05-23 (PR "C3"): the sub-folder split was first scoped — `perturbers/`,
  `theory/`, `electoral/` and `ui/` were created empty (`.gitkeep`), and the
  Election Lab central view ecosystem (`LabCentralView`, `LabOnboardingTour`,
  `ScenarioIO`) was migrated into a `lab/` folder as a proof of pattern. That
  ecosystem was later retired outright (folded into the Playground), so there
  is no `lab/` sub-folder here — only the target scaffold and its migration
  status survived. The `perturbers`/`electoral` names and grouping from that
  scaffold did not end up matching the panels' actual thematic content once
  read in full (e.g. "perturber" turned out to describe a shared UI pattern —
  every one of those panels renders a `PinToCentralButton` — rather than a
  content theme; several of its members belong to different labCatalog
  groups), so the actual 2026-09-12 migration below re-derived the grouping
  from `labCatalog.tsx` instead of carrying the old scaffold's names forward.
- 2026-09-12: full migration. All 63 files moved out of the flat top level
  into the 11 thematic sub-folders above; empty scaffold folders removed.
