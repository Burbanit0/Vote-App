// Polity i18n bundle (French — source of truth + type).
//
// The run explorer's vocabulary lives in its own namespace ("polity"), bundled
// in French like "playground" and lazy-loaded in English and pseudo. Components
// read it with `useTranslation('polity')`.

const polityFr = {
  masthead: {
    kicker: 'Polity — une société simulée',
    title: 'Explorateur de runs',
    subtitle:
      'Rejouez un run de la simulation, tick par tick : qui gouverne, qui se présente, qui vote et qui proteste.',
  },
  runPicker: {
    label: 'Run',
    option: '{{runId}} — {{population}} citoyens, {{years}} ans, graine {{seed}}',
  },
  runStates: {
    loadingRuns: 'Chargement des runs…',
    noRuns:
      'Aucun run à explorer : le serveur ne sert que le run de démonstration, ou les runs des dossiers listés dans POLITY_RUN_ROOTS.',
    runsError: 'Impossible de charger la liste des runs : {{message}}',
    loadingRun: 'Chargement du run…',
    runError: 'Impossible de charger ce run : {{message}}',
  },
  runFacts: {
    population: 'Population',
    populationValue: '{{count}} citoyens',
    duration: 'Durée',
    durationValue: '{{years}} ans · {{ticks}} ticks',
    engine: 'Moteur',
    engineLlm: 'modèle de langage',
    engineDeterministic: 'règles déterministes',
    votes: 'Bulletins journalisés',
    votesAll: 'tous',
    votesAuditSample: 'échantillon d’audit',
    votesNone: 'aucun',
    tick: 'Tick',
    tickValue: 'Année {{year}} · T{{quarter}}',
    partial: 'non confirmé : joué après le dernier checkpoint',
  },
};

export type PolityKeys = typeof polityFr;
export default polityFr;
