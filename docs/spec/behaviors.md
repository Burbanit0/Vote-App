# Behaviour catalogue (polity)

The invariants the polity simulator must keep, numbered so a test can say which one it
checks. A test that checks one is marked `@pytest.mark.behavior("ELE-01")` (several IDs
are allowed); `fast_api_voter/api/tests/test_behavior_catalogue.py` fails when an ID
below has no such test, when a test names an ID that is not here, or when an ID is
listed twice. The voting-rule axioms have their own matrix
(`test_voting_criteria_matrix.py`); this file is about the simulation around them.

The invariants a journal shows on its own (JRN-01/02, ELE-01/02/05/10, CIT-01/10) are
also checked line by line by `api/domain/polity/journal_invariants.py`, which
`test_polity_journal_invariants.py` runs over small runs Hypothesis draws: any seed,
population, mechanism switches and scripted amendments, not one hand-picked config.

Changing what an invariant says changes what the simulator promises: this file is
held for the owner's review like the tests it points to. Removing an ID needs the
same review, and its tests keep their marker until then.

Format of a row: `| ID | invariant | where it is stated |`, the last cell naming the
code, ADR or observation that states the rule (never the test that checks it). An ID
is three capital letters, a dash and two digits. Areas: ELE elections and
voting, LEG legislation, CON constitution, PAR parties, CIT citizens and
accountability, JRN the journal, DET determinism.

## Elections and voting

| ID | Invariant | Stated in |
|---|---|---|
| ELE-01 | Every legislative result allocates all of the assembly's seats in force (amendments included), or none when no party clears the threshold. | `ballot_and_aggregation.py` (`allocate_seats`) |
| ELE-02 | Over a run, the presidential outcomes (`elected`, `election_no_winner` or `election_invalidated`) and the legislative results match the electoral calendar: one per election tick, none elsewhere. A pending rerun or snap election replaces the presidential calendar until it resolves, and a successful `refuse_to_leave` cancels that tick's election. | `institutional_clock.py` |
| ELE-03 | A term-limited incumbent is never re-nominated. | `run_polity_simulation.py` (`run_simulation`) |
| ELE-04 | A barred candidate cannot declare a rupture candidacy. | `run_polity_simulation.py` (`_phase_rupture_candidacies`) |
| ELE-05 | An `elected` event never carries a `reason`. | `events.py` |
| ELE-06 | With every utility term at zero, a voter's utility ballot is exactly the positional ranking (`build_ranking`). | `simple_rules.py` |
| ELE-07 | With the policy weight at zero, a government's policy record changes no party choice and no ballot. | ADR-009 |
| ELE-08 | Every configured ranked and score method elects a unanimous winner, and empty ballots elect no one. | `ballot_and_aggregation.py` |
| ELE-09 | The winner of a rerun serves until the calendar's next election, not a full term from the rerun (OBS-041). | `observations.md` (OBS-041) |
| ELE-10 | A citizen casts at most one counted `vote_cast` per election tick; an audit ballot, journaled beside the utility vote, is never counted. | `events.py` (`VoteCast.audit`), `run_polity_simulation.py` |

## Legislation

| ID | Invariant | Stated in |
|---|---|---|
| LEG-01 | A bill moves at most `max_bill_dimensions` issues, each by at most `max_bill_step`. | `legislation.py` |
| LEG-02 | The assembly passes a bill only with strictly more than half of its seats. | `legislation.py` |
| LEG-03 | No bill is read without an assembly and a president, or outside the legislative interval. | `legislation.py` |
| LEG-04 | The president agent's kernel moves each position toward its target by at most the bound, and a turn out of bounds is rejected: the model never writes state directly. | `agents.py` |

## Constitution

| ID | Invariant | Stated in |
|---|---|---|
| CON-01 | A constitutional article only ever takes one of its legal values. | `constitution.py` (ADR-015) |
| CON-02 | The rules are re-validated after every amendment. | `constitution.py` (ADR-015) |
| CON-03 | A proposal made while another is pending, or with no chamber, is dropped. | `amendments.py` |
| CON-04 | Any legal constitution keeps the rules valid and the run completes, with one `constitution_amended` per changed article. | ADR-015 |

## Parties

| ID | Invariant | Stated in |
|---|---|---|
| PAR-01 | A party is led by its most ambitious member, and no citizen leads two parties. | `agents.py` (`party_leader`) |

## Citizens and accountability

| ID | Invariant | Stated in |
|---|---|---|
| CIT-01 | Legitimacy L(t) stays in [0, 1] over any sequence of ticks. | `legitimacy.py` |
| CIT-02 | At the neutral opinion-dynamics settings nobody moves; without drift, every citizen stays within the span of current and starting positions. | ADR-012 |
| CIT-03 | A generated population has positions in [0, 1], priorities summing to 1, thresholds in [0, 1], and every citizen starts an elector with no office, party or mandate. | `citizen.py`, `simple_rules.py` |
| CIT-04 | A target has at most one open petition, an active cooldown never coexists with an open petition, and no second petition launches during the cooldown. | `accountability.py`, `citizen.py` |
| CIT-05 | The office holder is never among the citizens consulted about them. | `accountability.py` |
| CIT-06 | The `pressure_action` context never carries `street_pressure`. | `llm_behavior_engine.py` |
| CIT-07 | Event salience never writes legitimacy or the representation gap directly. | ADR-023 |
| CIT-08 | The sortition chamber's occupancy never drops below its seat count. | `sortition_chamber.py` |
| CIT-09 | The electoral-only arm never returns a petition or a mobilize act. | `simple_rules.py` |
| CIT-10 | The population's mean emotions (`emotions_updated`) each lie in [0, 1]. | `emotions.py`, `events.py` (`EmotionsUpdated`) |

## The journal

| ID | Invariant | Stated in |
|---|---|---|
| JRN-01 | Events get sequential ids in write order, starting at 0 (or where a resumed journal left off). | `journal.py` (D8) |
| JRN-02 | Every journal line validates against its registered event type. | `events.py` |
| JRN-03 | `representative_response` is journaled once per presided tick. | `run_polity_simulation.py` |
| JRN-04 | `pressure_action` is journaled once per consulted citizen. | `run_polity_simulation.py` |
| JRN-05 | `chamber_deliberation` is journaled once per seated member per tick. | `run_polity_simulation.py` |
| JRN-06 | `reaction_to_event` is journaled once per citizen per firing event type. | `run_polity_simulation.py` |
| JRN-07 | Compaction is post-run and never changes a journal byte. | `run_polity_simulation.py` |
| JRN-08 | A codebook code is never reassigned; the retired code 7 stays retired. | `codebook.py` |

## Determinism

| ID | Invariant | Stated in |
|---|---|---|
| DET-01 | The same seed produces a byte-identical journal. | `run_polity_simulation.py` |
| DET-02 | A different seed produces a different journal. | `run_polity_simulation.py` (every RNG is seeded from `run.seed`) |
| DET-03 | A resumed run is byte-identical to an uninterrupted one. | `checkpoint.py` |
| DET-04 | The same seed produces the same population and the same sortition draw. | `citizen.py`, `sortition_chamber.py` |
| DET-05 | Enabling a mechanism that never triggers leaves the journal byte-identical to the default run. | `run_polity_simulation.py` (mechanisms journal only when they fire) |

## Candidates (stated, not yet tested)

Stated somewhere, with no test that checks them directly. They get an ID when a test
does:

- The founding config, its checkpoint hash and `config.json` never move. ADR-015
- The sortition chamber never initiates an amendment. ADR-015
- Each citizen's own emotions stay in [0, 1] (CIT-10 checks only the journaled
  population means). `emotions.py`, `citizen.py`
