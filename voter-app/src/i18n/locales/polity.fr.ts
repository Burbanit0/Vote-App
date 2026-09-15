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
  player: {
    label: 'Lecteur de ticks',
    slider: 'Tick du run',
    position: 'Année {{year}} · T{{quarter}} — tick {{tick}} sur {{last}}',
    play: 'Lire',
    pause: 'Pause',
    stepBack: 'Tick précédent',
    stepForward: 'Tick suivant',
    speed: 'Vitesse',
    speedValue: '{{speed}} ticks/s',
    keys: 'Espace : lecture · ← → : un tick · Page ↑ ↓ : une année · Début, Fin',
  },
  timeline: {
    title: 'Frise institutionnelle',
    summary: '{{terms}} mandats et {{events}} événements institutionnels sur {{ticks}} ticks',
    lanePresidency: 'Présidence',
    laneElections: 'Élections',
    laneAccountability: 'Contre-pouvoirs',
    laneLegislature: 'Législature',
    laneSociety: 'Société',
    term: 'Mandat du citoyen {{holder}}, dès le tick {{start}} ({{end}})',
    endedElection: 'terminé par une élection',
    endedRecall: 'rappelé : légitimité sous le plancher',
    endedConfidence: 'rappelé : vote de défiance perdu',
    endedRunEnd: 'en cours à la fin du run',
    jump: 'Tick {{tick}} : {{event}}',
    eventList: 'Événements, pour aller à leur tick',
    eventNames: {
      elected: 'élection gagnée',
      election_no_winner: 'élection sans vainqueur',
      election_invalidated: 'élection invalidée par le vote blanc',
      snap_election_triggered: 'élection anticipée convoquée',
      legislative_result: 'élections législatives',
      recalled: 'président rappelé',
      confidence_vote_triggered: 'vote de défiance ouvert',
      confidence_vote_result: 'résultat du vote de défiance',
      petition_launched: 'pétition lancée',
      petition_expired: 'pétition expirée',
      bill_proposed: 'projet de loi déposé',
      bill_enacted: 'loi adoptée',
      bill_blocked: 'projet de loi bloqué',
      coalition_formed: 'coalition formée',
      coalition_failed: 'coalition impossible',
      scandal_occurred: 'scandale',
      economic_shock_tick: 'choc économique',
      sortition_rotation: 'chambre tirée au sort renouvelée',
    },
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
