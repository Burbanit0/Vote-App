// Playground i18n bundle (French — source of truth + type).
//
// The playground/instrument vocabulary lives in its own namespace ("playground")
// rather than the already-large `translation` bundle, so it can grow without
// bloating the main locale and is lazy-loaded like `en`. Components read it with
// `useTranslation('playground')`.

const pgFr = {
  masthead: {
    kicker: 'Vote Lab — laboratoire de théorie du vote',
    title: 'Instrument de vote',
    subtitle:
      'Un seul appareil, du simple au complexe : choisissez la question, puis avancez moment par moment et lisez les effets en direct.',
  },
  mode: {
    leader: 'Dirigeant',
    assembly: 'Assemblée',
  },
  moments: {
    electorate: { label: 'Électorat', hint: 'Qui vote, comment il se distribue et se comporte.' },
    method: { label: 'Méthode', hint: 'La règle de décompte et la forme du bulletin.' },
    strategy: { label: 'Stratégie', hint: 'Vote utile, vote blanc, manipulation.' },
    campaign: { label: 'Campagne', hint: 'La réaction du vote dans le temps.' },
    bilan: { label: 'Bilan', hint: 'Le verdict — ce que ça vaut, selon vos valeurs.' },
  },
  guided: {
    start: 'Début',
    restart: '↻ Recommencer',
    moment: 'Moment {{n}} / {{total}}',
    next: '{{label}} →',
  },
  explore: {
    heading: 'Pour aller plus loin',
  },
  anchors: {
    mechanisms: {
      title: '⚙️ Autres procédures de décision',
      subtitle: '11 mécanismes (jury, sortition, délégation…)',
    },
    systems: {
      title: '🔬 Systèmes & circonscriptions',
      subtitle: '7 vues (coalitions, districts, gerrymander…)',
    },
    results: {
      title: '📋 Résultats complets (dépouillement)',
      subtitle: 'toutes les méthodes · animation',
    },
    analysis: {
      title: '🔬 Analyse approfondie du résultat courant',
      subtitle: 'distributions · regret · manipulabilité',
    },
    theory: {
      title: '🔬 Théorie & paradoxes du choix social',
      subtitle: 'Sen · jugements · McKelvey · pouvoir · recul démocratique…',
    },
  },
  common: {
    loading: 'Chargement…',
  },
};

export type PlaygroundKeys = typeof pgFr;
export default pgFr;
