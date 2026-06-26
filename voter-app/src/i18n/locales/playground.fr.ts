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
    candidates: 'candidats',
    parties: 'partis',
    voters: 'électeurs',
  },
  electorate: {
    composeTitle: '🧭 Composer l’électorat',
    composeSubComposed: '{{count}} communautés · mélange',
    composeSubSimple: 'gaussien simple',
    startLabel: 'Point de départ (synthétique)',
    summary: '{{points}} {{pointWord}} · {{voters}} électeurs · {{ideology}}',
    dimsLabel: 'Dimensions de l’espace',
    dims1: '1D — un seul axe',
    dims2: '2D — deux axes',
    dims3: '3D — trois axes',
    sourceLabel: 'Source des préférences',
    sourceSpatial: 'Spatiale (carte)',
    sourceImpartial: 'Culture impartiale',
    sourceMallows: 'Mallows',
    sourceUrn: 'Urne de Pólya',
    sourceHandcrafted: 'Matrice sur mesure',
    behaviorLabel: 'Comportement des électeurs',
    behaviorSincere: 'Sincère',
    behaviorStrategic: 'Stratégique',
    behaviorMixed: 'Mixte',
    valence: 'Valence (qualité hors-idéologie)',
    participationTitle: 'Participation (abstention)',
    abstentionModelLabel: 'Modèle d’abstention',
    abstentionFull: 'Participation totale',
    abstentionAlienation: 'Aliénation (trop loin de tous)',
    abstentionIndifference: 'Indifférence (départage trop serré)',
    intensity: 'Intensité : {{pct}} %',
    turnoutLabel: 'Taux de participation :',
    turnoutAbstentions: '({{count}} abstentions)',
    downsNote:
      'Abstention de Downs : aliénation (même le meilleur choix est trop loin) ou indifférence (pas d’écart net entre les deux premiers).',
    abstentionAnchorTitle: '🔬 Abstention différentielle (analyse)',
    abstentionAnchorSub: 'distribution complète',
  },
  method: {
    note: 'La règle de décompte et la vue se choisissent directement sur l’instrument →. Ici, réglez ce que l’électeur peut exprimer.',
    ballotTitle: 'Bulletin (expression)',
    ballotTypeLabel: 'Type de bulletin',
    ballot: {
      full: 'Information complète',
      choose_one: 'Choix unique (1 croix)',
      approve: 'Approbation',
      rank_full: 'Classement complet',
      rank_truncated: 'Classement tronqué (top-k)',
      score: 'Notes (échelle)',
      grade: 'Mentions (JM)',
      cumulative: 'Cumulatif (budget de points)',
    },
    truncateLabel: 'Classer le top {{n}}',
    levelsLabel: 'Niveaux : {{n}}',
    expressiveness: 'Expressivité',
    cognitiveLoad: 'Charge cognitive',
    flips_one:
      '⚠ À règle égale, ce bulletin change le vainqueur pour {{count}} méthode : {{list}}.',
    flips_other:
      '⚠ À règle égale, ce bulletin change le vainqueur pour {{count}} méthodes : {{list}}.',
    incompatible:
      '{{count}} méthodes exclues (l’information du bulletin ne permet pas de les dépouiller honnêtement).',
    blankAnchorTitle: '🔬 Divergence du vote blanc (analyse)',
    blankAnchorSub: 'règle du blanc',
    assemblyTitle: 'Assemblée',
    structureLabel: 'Structure',
    structurePr: 'Proportionnelle (listes)',
    structureFptp: 'Circonscriptions (FPTP)',
    structureMmp: 'Mixte (MMP)',
    seatsLabel: 'Sièges : {{n}}',
    thresholdLabel: 'Seuil : {{pct}} %',
    apportionmentLabel: 'Répartition des sièges',
    dhondt: 'D’Hondt',
    sainteLague: 'Sainte-Laguë',
  },
  strategy: {
    sincereTitle: '🗳️ Vote sincère ou vote utile ?',
    sincereHint:
      'Votre conviction, méthode par méthode — glissez le losange « Vous » sur la carte.',
    vulnTitle: '⚡ Vulnérabilité stratégique (Gibbard–Satterthwaite)',
    vulnSub: 'à la demande · lent',
    manipTitle: 'Manipulation : principe vs pratique',
    manipPrinciple: 'Jouable en principe (Gibbard–Satterthwaite) · calcul du bon mensonge :',
    probeIntro: 'Sonde sur cet électorat :',
    probeCoalition: 'une coalition de {{pct}} % suffit (compromission naïve)',
    probeNone: 'aucune compromission naïve ≤ 40 % ne renverse le vainqueur ici',
    probeBackfire: ' · des tentatives se retournent contre la coalition',
    exampleIntro: 'Exemple :',
    examplePluralityOk: 'sous pluralité, {{pct}} % suffisent',
    examplePluralityFail: 'sous pluralité, la compromission échoue ici',
    exampleIrvMid: ' ; la même stratégie sous IRV ',
    exampleIrvDemands: 'demande {{pct}} %',
    exampleIrvFail: 'échoue',
    exampleIrvBackfire: ' (et peut se retourner contre elle)',
    assemblyTitle: 'Stratégie d’assemblée',
    duverger: 'Désertion stratégique (Duverger)',
    duvergerTitle:
      'Les électeurs désertent les partis non viables (FPTP : hors du top-2 de leur circonscription ; proportionnelle : sous le seuil) pour leur parti viable le plus proche — la loi de Duverger en mécanique.',
    duvergerNote:
      'La désertion comprime les partis non viables vers leur voisin viable : Duverger, en mécanique. L’effet se lit en direct sur la composition de l’assemblée →.',
  },
  bilan: {
    evaluatedFor: 'Évalué pour :',
    sensibility: 'Votre sensibilité',
    fineTune: 'Réglage fin…',
    simpleDial: '← Cadran simple',
    majoritarian: 'Majoritaire (décisif)',
    consensualist: 'Consensualiste (inclusif)',
    bandNote: '{{count}} ré-échantillonnages',
  },
  campaign: {
    emptyPrompt:
      'Composez d’abord un électorat dans le moment ① Électorat, puis revenez lancer une campagne.',
    deepTitle: '🔬 Explorations approfondies',
    deepSub: 'trajectoire · mécanismes temporels · réalisme comportemental',
    deepTrajectory: '🎬 Approfondir la trajectoire',
    deepMechanisms: '🔁 Mécanismes & comportements dans le temps',
    deepRealism: '🧠 Réalisme comportemental (un scrutin)',
  },
  instrument: {
    labelLeader: 'Carte idéologique — dirigeant',
    labelAssembly: 'Composition de l’assemblée',
    flipCaption: 'Mêmes électeurs, caractère opposé.',
    paradox: 'paradoxe {{pct}} %',
    paradoxLoading: '· · ·',
    paradoxTitle:
      'Part des électorats ré-échantillonnés sans vainqueur de Condorcet — un taux élevé signale que le résultat dépend fortement des hypothèses.',
    condorcet: 'Condorcet : {{name}}',
    condorcetNone: 'aucun vainqueur de Condorcet (cycle)',
    shake: '🎲 Secouer les hypothèses',
    shakeTitle:
      "Ré-échantillonne l'électorat 60 fois (mêmes hypothèses, nouveaux tirages) — sépare une propriété structurelle d'un réglage choisi.",
    shakeHint: 'Monte-Carlo complet dans les Explorations avancées (Analyse)',
    shakeHoldsMid: 'tient',
    shakeHoldsEnd: 'des {{count}} ré-échantillonnages.',
    democracyTitle: '🗺 Carte des démocraties (Lijphart)',
    democracySub: 'majoritaire ↔ consensus',
    democracyComputing: 'Calcul en cours…',
    issuesTitle: '🗳 Enjeux & groupage (Ostrogorski)',
    structuralTitle: '⚖ Équités structurelles',
  },
};

export type PlaygroundKeys = typeof pgFr;
export default pgFr;
