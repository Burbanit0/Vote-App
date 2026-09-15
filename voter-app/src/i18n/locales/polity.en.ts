// Polity i18n bundle (English). Mirrors polity.fr.ts exactly (typed).
import type { PolityKeys } from './polity.fr';

const polityEn: PolityKeys = {
  masthead: {
    kicker: 'Polity — a simulated society',
    title: 'Run explorer',
    subtitle:
      'Replay a simulation run, tick by tick: who governs, who runs, who votes and who protests.',
  },
  runPicker: {
    label: 'Run',
    option: '{{runId}} — {{population}} citizens, {{years}} years, seed {{seed}}',
  },
  runStates: {
    loadingRuns: 'Loading runs…',
    noRuns:
      'No run to explore: the server serves only the demonstration run, or the runs in the folders listed in POLITY_RUN_ROOTS.',
    runsError: 'Could not load the list of runs: {{message}}',
    loadingRun: 'Loading the run…',
    runError: 'Could not load this run: {{message}}',
  },
  runFacts: {
    population: 'Population',
    populationValue: '{{count}} citizens',
    duration: 'Duration',
    durationValue: '{{years}} years · {{ticks}} ticks',
    engine: 'Engine',
    engineLlm: 'language model',
    engineDeterministic: 'deterministic rules',
    votes: 'Journaled ballots',
    votesAll: 'all',
    votesAuditSample: 'audit sample',
    votesNone: 'none',
    tick: 'Tick',
    tickValue: 'Year {{year}} · Q{{quarter}}',
    partial: 'unconfirmed: played after the last checkpoint',
  },
};

export default polityEn;
