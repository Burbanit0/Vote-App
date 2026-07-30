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
  stories: {
    launch: 'Histoires',
    launchHint: 'Des récits guidés qui font surgir un phénomène sous vos yeux, dans l’instrument.',
    pick: 'Choisir une histoire',
    close: 'Fermer',
    quit: 'Quitter',
    step: 'Scène {{n}} / {{total}}',
    next: 'Suivant →',
    prev: '← Précédent',
    restart: '↻ Rejouer',
    replayHint: 'Vous reprenez la main : l’instrument reste sur la dernière scène.',
    spoiler: {
      title: 'L’effet spoiler',
      tagline: 'Un troisième candidat qui ne peut pas gagner peut quand même décider du vainqueur.',
      steps: {
        duel: 'Deux candidats sur un axe gauche–droite : en scrutin majoritaire, Gore l’emporte face à Bush.',
        enter:
          'Nader entre à gauche. Il ne gagnera pas — mais il divise le vote de gauche, et Bush passe devant. C’est le spoiler.',
        irv: 'Mêmes électeurs, autre règle : au vote alternatif (IRV), Nader est éliminé, ses voix reviennent à Gore, qui l’emporte.',
        condorcet:
          'En méthode de Condorcet aussi, Gore gagne : c’est lui que la majorité préfère en duel. Le spoiler n’était qu’un artefact du scrutin majoritaire.',
      },
    },
    squeeze: {
      title: 'L’étau du centre',
      tagline: 'Le candidat que tout le monde accepte peut être éliminé le premier.',
      steps: {
        field:
          'Trois candidats alignés — Gauche, Centre, Droite — face à un électorat polarisé. Peu d’électeurs placent le Centre en premier.',
        condorcet:
          'Pourtant le Centre bat la Gauche ET la Droite en duel : c’est le vainqueur de Condorcet, le compromis que la majorité préfère.',
        irv: 'Au vote alternatif, le Centre — faible en premiers choix — est éliminé d’entrée, et c’est un extrême qui l’emporte. Le centre a été pris en étau.',
      },
    },
    paradox: {
      title: 'Ça dépend qui compte',
      tagline: 'Un même électorat, trois méthodes, trois vainqueurs — lequel est le « vrai » ?',
      steps: {
        plurality:
          'Trois blocs dont les préférences tournent en rond (A ≻ B ≻ C ≻ A). En scrutin majoritaire, Alice l’emporte.',
        irv: 'Changez pour le vote alternatif : c’est Carol qui gagne, avec exactement les mêmes bulletins.',
        approval:
          'Passez au vote par approbation : cette fois, c’est Bob. Trois méthodes, trois vainqueurs.',
        condorcet:
          'En duel un-contre-un, Alice bat les deux autres — la vainqueure de Condorcet. Et pourtant ni l’IRV ni l’approbation ne l’ont désignée : la méthode, à elle seule, change le président.',
      },
    },
    utile: {
      title: 'La course au vote utile',
      tagline: 'Quand la règle vous pousse à trahir votre favori.',
      steps: {
        sincere:
          'Vous êtes à gauche. Votre cœur va à Écolo — mais en scrutin majoritaire, voter Écolo risque de faire gagner la Droite.',
        tempt:
          'La tentation du « vote utile » : abandonner Écolo pour Gauche, plus solide, afin de barrer la Droite. Le scrutin majoritaire récompense ce calcul.',
        approval:
          'Au vote par approbation, vous approuvez Écolo ET Gauche sans vous diviser : plus besoin de trahir votre favori.',
        irv: 'Au vote alternatif, classez Écolo en premier sans risque : si elle est éliminée, votre voix glisse vers Gauche. La sincérité redevient sûre.',
      },
    },
    valence: {
      title: 'Majorité contre bien-être',
      tagline: 'Le mieux placé n’est pas toujours celui qui rendrait le plus service.',
      steps: {
        position:
          'Deux candidats sur l’axe. Le Sortant, proche du centre, l’emporte sur la seule position — le favori géographique.',
        quality:
          'Activez la valence (la qualité non idéologique) : le Réformateur, un peu excentré mais bien plus compétent, devient le choix qui maximise le bien-être. La position ne dit pas tout.',
      },
    },
    five: {
      title: 'Un électorat, plusieurs présidents',
      tagline: 'France 2002 : les mêmes bulletins, un vainqueur différent selon la méthode.',
      steps: {
        plurality:
          'Huit candidats, électorat polarisé. En scrutin majoritaire à un tour, Chirac arrive en tête.',
        irv: 'Au vote alternatif, les reports changent tout : c’est Jospin qui l’emporte.',
        borda: 'En méthode de Borda, qui récompense les consensus, Bayrou passe devant.',
        condorcet: 'Condorcet confirme Bayrou : c’est lui qui bat le plus d’adversaires en duel.',
        approval:
          'Le vote par approbation couronne lui aussi Bayrou. Bilan : plusieurs présidents pour un seul électorat — la méthode n’est pas neutre.',
      },
    },
    clones: {
      title: 'La stratégie du clone',
      tagline:
        'Un candidat peut se faire élire en alignant un allié presque identique à lui — mais pas avec n’importe quelle méthode.',
      steps: {
        duel: 'Deux candidats sur l’axe gauche–droite. En méthode de Borda, B rassemble 54 % de l’électorat et l’emporte largement.',
        clone:
          'Le camp de A aligne un second candidat, A2, presque identique à A mais un peu plus à gauche. Aucun électeur n’a changé d’avis — et pourtant, en Borda, c’est désormais A qui gagne.',
        condorcet:
          'Avec Condorcet, le clonage ne sert à rien : B bat toujours A ET A2 en duel, donc B reste vainqueur. La faille était propre à Borda.',
        irv: 'Au vote alternatif (IRV) non plus : B, toujours préféré par la majorité, l’emporte quel que soit le nombre de clones alignés en face.',
      },
    },
    blank: {
      title: 'Le vote blanc, quatre destins',
      tagline:
        'Les mêmes électeurs, le même bulletin — la règle qui compte le blanc décide de tout.',
      steps: {
        clean:
          'Camille l’emporte avec 67 % des voix face à Farid, à 33 %. Une victoire nette — parmi ceux qui ont choisi quelqu’un.',
        todayLaw:
          'Activez le vote blanc : 62 % de l’électorat est trop loin des deux candidats et rejette le choix. La loi française actuelle l’exclut du décompte — Camille reste élue, à 96 % des rares voix exprimées.',
        ifCounted:
          'Comptez le blanc dans les exprimés : la part de Camille retombe à 36 % de l’ensemble des votants. Sous la barre des 50 %, plus de mandat clair.',
        competitive:
          'Traitez le blanc comme un candidat, régime uruguayen : à 62 %, il devance Camille et Farid réunis. La candidature est rouverte.',
      },
    },
    monotonie: {
      title: 'Gagner des voix, perdre l’élection',
      tagline:
        'Sous le vote alternatif, convaincre de nouveaux électeurs peut, dans certains cas, vous faire perdre.',
      steps: {
        avant:
          'Vote alternatif (IRV), trois candidats. Premiers choix : Nora 38 %, Karim 32 %, Yanis 29 %. Yanis, le moins soutenu, est éliminé — ses voix se reportent sur Nora, qui l’emporte.',
        apres:
          'Un groupe d’indécis, qui plaçait Karim en tête et Nora juste derrière, se laisse convaincre par Nora et la place désormais en tête. Son score de premier choix grimpe à 49 %. Et pourtant : c’est Karim qui est maintenant le moins soutenu, il est éliminé, et son report élit Yanis. Nora a gagné des voix — et perdu l’élection.',
      },
    },
    renversement: {
      title: 'Le vote à l’envers',
      tagline:
        'Inversez tous les bulletins : le scrutin majoritaire peut réélire le même vainqueur.',
      steps: {
        avant:
          'Malik réunit une base fidèle (39 %) ; Inès (33 %) et Sami (28 %) se partagent le reste. Au scrutin majoritaire à un tour, Malik l’emporte.',
        inverse:
          'Retournez chaque bulletin — le premier choix de chacun devient son dernier, et inversement. Résultat : Malik l’emporte à nouveau, cette fois avec 61 % des voix. Il était déjà le candidat le plus rejeté par le reste de l’électorat : le scrutin majoritaire ne distingue pas le plus aimé du plus détesté, il ne regarde que qui arrive en tête.',
      },
    },
    seuil: {
      title: 'Le seuil qui efface',
      tagline: 'Une barre à 5 % ne retire pas que des sièges : elle déplace les voix.',
      steps: {
        pur: 'Proportionnelle intégrale, 100 sièges, aucun seuil. Cinq partis, et les Souverainistes — 3,4 % des voix — obtiennent 3 sièges. L’assemblée est un miroir presque exact de l’électorat.',
        barre:
          'Activez le seuil de 5 % : les Souverainistes tombent à zéro siège. Leurs 3,4 % deviennent des voix perdues, et leurs sièges sont redistribués aux partis déjà représentés.',
        desertion:
          'Ajoutez le vote stratégique : sachant leur parti condamné par le seuil, ces électeurs se reportent sur la Droite, qui passe de 21 % à 25 %. Le seuil n’a pas seulement effacé un parti — il a fabriqué une majorité ailleurs.',
      },
    },
    structures: {
      title: 'Un vote, trois parlements',
      tagline: 'Mêmes bulletins, mêmes partis : proportionnelle, uninominal ou mixte ?',
      steps: {
        pr: 'Proportionnelle nationale : chaque parti reçoit à peu près sa part de voix. L’indice de Gallagher (la distorsion voix→sièges) est très bas.',
        fptp: 'Passez au scrutin uninominal par circonscription : le Centre, 35 % des voix, rafle 41 % des sièges, tandis que les Verts — pourtant à 19 % — tombent à 9 %, faute d’être majoritaires quelque part. Près d’un tiers des voix ne pèse plus rien.',
        mmp: 'En scrutin mixte compensatoire, les élus locaux sont conservés mais des sièges de compensation rétablissent les proportions : on retrouve la fidélité de la proportionnelle sans perdre l’ancrage territorial.',
      },
    },
    diviseur: {
      title: 'Le diviseur décide',
      tagline: 'Deux façons d’arrondir la proportionnelle — deux assemblées.',
      steps: {
        dhondt:
          'Assemblée de 21 sièges, sans seuil, méthode d’Hondt. Le Centre obtient 8 sièges, les Souverainistes aucun : d’Hondt arrondit systématiquement en faveur des grands.',
        sainteLague:
          'Même électorat, méthode Sainte-Laguë : le Centre redescend à 7 sièges et les Souverainistes en gagnent 1. Aucun électeur n’a changé d’avis — seule la formule d’arrondi a changé.',
      },
    },
  },
  common: {
    loading: 'Chargement…',
    candidates: 'candidats',
    parties: 'partis',
    voters: 'électeurs',
  },
  robustness: {
    summary: '{{name}} l’emporte dans {{pct}} % des {{n}} tirages',
    aria: 'Robustesse : {{name}} gagne dans {{pct}} % de {{n}} ré-échantillons de l’électorat',
    fragile: '— verdict fragile',
  },
  scene: {
    drag: 'Glissez pour pivoter',
    pauseSpin: '⏸ rotation',
    playSpin: '▶ rotation',
    aria: 'Vue 3D de l’électorat',
  },
  timeline: {
    thesisAt: 'Au',
    thesisWins: 'l’emporte. En campagne, le résultat peut',
    thesisMove: 'bouger',
    subtitle: 'Choisissez un scénario, puis avancez le temps pour voir si le vainqueur tient.',
    scenarioLabel: 'Scénario',
    scenarioAria: 'Scénario de campagne',
    scenarios: {
      derive: {
        label: 'Dérive (Hotelling)',
        blurb: 'Les candidats convergent vers l’électeur médian.',
      },
      sondages: {
        label: 'Sondages',
        blurb: 'Convergence perturbée par la volatilité des sondages (pic à mi-campagne).',
      },
      durcissement: {
        label: 'Durcissement',
        blurb: 'Les candidats radicalisent leurs positions (s’éloignent du médian).',
      },
      meilleure_reponse: {
        label: 'Meilleure réponse (Downs)',
        blurb:
          'Chaque candidat se déplace là où il maximise son score — sous LA règle choisie. Changez de méthode : l’équilibre se déplace.',
      },
    },
    method: 'Méthode',
    intensity: 'Intensité',
    intensityTitle: 'Distance parcourue par les candidats d’ici la fin de campagne.',
    rounds: 'Tours',
    mapLabel: 'Idéologie — dérive',
    trajLabel: 'Trajectoire — valeur du résultat',
    centrality: 'centralité',
    optimality: 'optimalité',
    trajAria: 'Trajectoire de la valeur du résultat au cours de la campagne',
    caption:
      'Ruban du bas = vainqueur ; un changement de couleur (trait vertical) est une bascule. Optimalité = 1 − regret.',
    winnerAt: 'Vainqueur (J{{day}})',
    flip: 'bascule depuis J0',
    condorcetNone: 'Pas de vainqueur de Condorcet (cycle)',
    condorcetHeld: '✓ Vainqueur de Condorcet respecté',
    condorcetBroken: '✗ Condorcet non respecté (CW : {{cw}})',
    regret: 'Regret',
    centralityMeter: 'Centralité',
    day: 'Jour',
    round: 'Tour',
    betweenRounds: 'entre deux tours',
    scrubberAria: 'Avancement de campagne',
    roundTitle: 'Tour {{n}}',
    pause: '⏸ Pause',
    play: '▶ Jouer la campagne',
    prevRound: '◀ Tour préc.',
    nextRound: 'Tour suiv. ▶',
    resetJ0: '↺ J0',
    pinTitle:
      'Reporte les positions actuelles des candidats dans le playground comme nouvel état de départ. C’est la seule action qui modifie le playground.',
    pin: '📌 Épingler dans le playground',
    pinned: '✓ Positions reportées dans le playground (J{{day}}).',
    mapAria: 'Carte idéologique — les candidats dérivent au cours de la campagne',
  },
  anchorBody: {
    blank: {
      intro:
        'Ne pas choisir n’est pas rien : abstention, vote blanc, « aucun de ces candidats ». Un thème à part — parce que ce que la règle fait du refus peut tout changer.',
    },
    mechanisms: {
      intro:
        'D’autres mécanismes de décision collective que l’élection classique — chacun sur le même électorat, calculé à la demande.',
      jury: '⚖️ Théorème du jury (Condorcet)',
      nota: '🚫 Vote NOTA (aucun des candidats)',
      liquid: '💧 Démocratie liquide (délégation)',
      sortition: '🎲 Sortition (tirage au sort)',
      deliberation: '🗣️ Délibération puis vote',
      conviction: '🪙 Vote par conviction',
      epistocracy: '🎓 Épistocratie (vote pondéré par compétence)',
      identity: '🪪 Vote identitaire',
    },
    analysis: {
      intro:
        'Mesures comparatives approfondies sur le même électorat — distributions, regret, manipulabilité, volonté collective. Chaque module se calcule à la demande.',
      montecarlo: '🎲 Monte-Carlo (distributions)',
      manipulability: '🕵 Manipulabilité (par méthode)',
      manipulation: '🎯 Analyse de manipulation',
      collective: '🤝 Volonté collective',
      assumptions: '🧪 Test des hypothèses',
      combined: '🧮 Effets combinés (factoriel)',
    },
    results: {
      intro:
        'Le résultat « brut » de l’élection sur l’électorat partagé : la table de toutes les méthodes et le dépouillement animé.',
      table: '📋 Résultats complets (toutes méthodes)',
      animation: '🎬 Dépouillement animé',
    },
    systems: {
      intro:
        'Systèmes électoraux et géographie : sièges, coalitions, circonscriptions, bulletin. Chaque module se calcule à la demande.',
      coalition: '🤝 Coalitions',
      multiwinner: '🪑 Multiwinner (STV/SPAV/Phragmén)',
      districts: '🗺️ Circonscriptions',
      gerrymander: '✂️ Charcutage (gerrymander)',
      stv: '🔁 Vote unique transférable (STV)',
      ballot: '📋 Complexité du bulletin',
      pipeline: '🎬 Pipeline d’élection (animation)',
    },
    campaign: {
      intro:
        'Le scrubber ci-dessus montre une trajectoire (les candidats dérivent vers l’électeur médian). Ces quatre étapes l’approfondissent : l’équilibre visé, l’effet des sondages, l’impact de la polarisation, puis l’évolution du système de partis sur plusieurs élections.',
      hotelling: '① 📐 Vers quel équilibre ? (Hotelling-Downs)',
      campaign: '② 📣 Effet des sondages (sensibilité de campagne)',
      polarization: '③ ↔️ Électorat polarisé (qualité du résultat)',
      party: '④ 🏳️ Évolution des partis (Duverger sur la durée)',
    },
    theory: {
      intro:
        'Les paradoxes du choix social et la théorie démocratique — les limites formelles que toute règle de vote doit affronter. Chaque module se calcule à la demande.',
      sen: '🔓 Paradoxe de Sen (libéral parétien)',
      judgment: '🧩 Agrégation de jugements (dilemme discursif)',
      agenda: '🎚️ Manipulation d’agenda (McKelvey)',
      tyranny: '👥 Tyrannie de la majorité',
      apportionment: '🧮 Apportionnement (Balinski-Young)',
      power: '⚖️ Indices de pouvoir (Shapley-Shubik, Banzhaf)',
      backsliding: '📉 Recul démocratique (Levitsky-Ziblatt)',
      intergen: '⏳ Représentation intergénérationnelle',
      polis: '🗣️ Pol.is (clustering délibératif)',
    },
    breal: {
      intro:
        'Le résultat du playground suppose des électeurs idéaux. Ici, le comportement réel déforme un même scrutin — biais d’ordre, vote timide, surcharge de choix, participation différentielle, polarisation affective. Chaque module se calcule à la demande.',
      biases: '📊 Biais de vote (ordre, ancrage)',
      shyvoter: '🤐 Électeur timide (effet Bradley)',
      overload: '🤯 Surcharge de choix',
      compulsory: '🗳️ Vote obligatoire',
      demographic: '👥 Participation par démographie',
      affective: '🔥 Polarisation affective',
    },
    tdyn: {
      intro:
        'Les phénomènes qui se déploient dans le temps — sur plusieurs tours ou par effet de séquence. Chacun part du même électorat (état J0) et se calcule à la demande.',
      adaptive: '⚙️ Vote adaptatif (tactique sur durée)',
      replay: '🕰️ Rejeu historique',
      primary: '🥇 Primaires',
      cascade: '🌊 Cascade d’information',
      fatigue: '😮‍💨 Fatigue électorale',
    },
  },
  canvas: {
    ruleLabel: 'Règle',
    winnerLabel: 'Vainqueur :',
    replayCta: '▶ Voir le déroulé',
    viewLabel: 'Vue',
    lensWinner: 'Vainqueur',
    lensManipulation: 'Manipulation',
    lensProbability: 'Probabilité',
    lensCriteria: 'Critères',
    view3d: '🧊 Vue 3D',
    viewPlane: '▦ Plan x–y (édition)',
    svgAria: 'Carte idéologique — élire un dirigeant',
    manipCompromise: 'Tenté par le vote utile (abandonne son favori)',
    manipBurying: 'Tenté d’enterrer un rival (le classe trop bas)',
    manipSafe: 'Reste sincère (rien à gagner à tricher)',
    manipUnder: 'Sous',
    manipMid:
      ' : {{pct}}% des électeurs tentés de voter stratégiquement ({{compromise}} compromis · {{burying}} enterrement). Vote au sort :',
    manipEnd:
      ' — la seule règle inmanipulable (Gibbard 1977). Toute règle ordinale déterministe est manipulable : c’est la frontière de Gibbard-Satterthwaite.',
    methodHeader: 'Méthode',
    criteriaLegend:
      '✓ satisfait · ✗ violé · – non déclenché sur cet électorat. Mesuré en direct — glissez un candidat pour provoquer une violation. Le vainqueur de Condorcet est cerclé sur la carte.',
    condorcetMarker: 'Condorcet',
    lotteryTitle: 'Loterie du vote au sort — probabilité de victoire (= part des premières voix)',
    zAxis: 'Axe z (profondeur) — réglé par curseur',
    entrantZone: 'Zone d’un nouvel entrant',
    youMarker: 'Vous',
    capManip:
      'Lentille Manipulation : chaque électeur est traité comme un bloc de conviction ; sa couleur dit si la règle le pousse à voter utile. Glissez un candidat ou changez de règle — les tentations se redessinent. ',
    capCriteria:
      'Lentille Critères : matrice axiomatique mesurée sur CET électorat. Le vainqueur de Condorcet (s’il existe) est cerclé sur la carte — comparez-le au vainqueur de la règle choisie. ',
    capProbability:
      'Lentille Probabilité : sous le vote au sort, un bulletin est tiré au hasard — l’intensité montre la chance de victoire d’un nouvel entrant, et chaque bassin devient une probabilité (et non une frontière nette). ',
    capDims1:
      'Espace à 1 dimension : tout se joue sur un axe — le terrain du théorème de l’électeur médian.',
    capDims2:
      'Glissez les candidats. Les zones colorées montrent qui gagnerait si un candidat était placé là — les frontières révèlent les régions vulnérables au vote stratégique.',
    capDims3Scene:
      'Vue 3D orbitale : glissez pour pivoter, les électeurs sont colorés par candidat le plus proche (en 3-D). Basculez en « Plan x–y » pour éditer et voir l’overlay.',
    capDims3Plane:
      'Plan x–y (réglez z au curseur) ; le calcul du vainqueur est bien en 3-D, mais l’overlay n’est qu’une tranche z=0.',
  },
  electorate: {
    composeTitle: '🧭 Composer l’électorat',
    composeSubComposed: '{{count}} communautés · mélange',
    composeSubSimple: 'gaussien simple',
    startLabel: 'Point de départ',
    startModels: 'Modèles théoriques',
    startElections: 'Inspirés d’élections',
    summary: '{{points}} {{pointWord}} · {{voters}} électeurs · {{ideology}}',
    advancedTitle: '⚙ Réglages avancés',
    advancedSubtitle: 'dimensions, source, valence, comportement, participation',
    dimsLabel: 'Dimensions de l’espace',
    dims1: '1D — un seul axe',
    dims2: '2D — deux axes',
    dims3: '3D — trois axes',
    dimsLockedSingle:
      'Verrouillé en 1D : le single-peaked suppose un axe unique (théorème de Black).',
    sourceLabel: 'Source des préférences',
    sourceGroupSpatial: 'Spatiales (candidats placés)',
    sourceGroupCulture: 'Cultures statistiques (biplot)',
    source_spatial: 'Spatiale (euclidienne)',
    source_single_peaked: 'Single-peaked (1 axe)',
    source_impartial: 'Culture impartiale (IC)',
    source_iac: 'Culture impartiale anonyme (IAC)',
    source_mallows: 'Mallows (consensus)',
    source_urn: 'Urne de Pólya',
    source_plackett_luce: 'Plackett–Luce (qualité)',
    source_didi: 'Dirichlet (DiDi)',
    source_stratification: 'Stratification (strates)',
    param_mallows: 'Dispersion φ = {{value}} (0 = consensus, 1 = chaos)',
    param_urn: 'Contagion α = {{value}} (petit = mimétisme fort)',
    param_plackett_luce: 'Gradient de qualité = {{value}}',
    param_didi: 'Concentration = {{value}} (haut = électeurs corrélés)',
    param_stratification: 'Part de la strate supérieure = {{value}}',
    nonSpatialNote:
      'Cette culture n’a pas de géométrie de candidat : la carte devient un biplot en lecture seule (positions déduites des bulletins) et les candidats ne sont plus déplaçables. Le taux de paradoxe, lui, réagit.',
    behaviorLabel: 'Comportement des électeurs',
    behaviorSincere: 'Sincère',
    behaviorStrategic: 'Stratégique',
    behaviorMixed: 'Mixte',
    valence: 'Valence (qualité hors-idéologie)',
    valenceHint:
      'Qualité non-idéologique par candidat (compétence, notoriété…) : utilité = −distance + valence. Une valence forte peut faire gagner un candidat non central.',
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
    multiSelectNote:
      'Cochez les méthodes à comparer. Seules les méthodes cochées apparaissent dans le bilan et la carte des valeurs.',
    family: {
      majoritarian: 'Majoritaires',
      positional: 'Positionnelles',
      condorcet: 'Condorcet',
      cardinal: 'Cardinales',
      other: 'Autres',
    },
    selectAll: 'Tout cocher',
    enabledCount: '{{count}} / {{total}} méthodes actives',
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
    intro:
      'Un électeur « stratégique » ne vote pas pour son favori mais pour le candidat le mieux placé qui lui convient — le « vote utile ». Sur la carte, les points colorés sont les électeurs qui auraient intérêt à le faire ; les gris n’ont rien à y gagner. Moins il y a de couleur, plus la méthode résiste à la manipulation.',
    behaviorHint:
      'Sincère : chacun vote selon sa vraie préférence. Stratégique : les électeurs tentés désertent leur favori. Mixte : un mélange des deux.',
    tacticTitle: 'Tactique du bloc',
    tacticLabel: 'Comment le bloc ment',
    tacticCompromise: 'Vote utile (compromis)',
    tacticBurying: 'Enterrement',
    tactic_compromise_desc:
      'Le bloc classe en tête un candidat moins aimé mais mieux placé, pour éviter que sa voix soit « perdue ».',
    tactic_burying_desc:
      'Le bloc garde son favori en tête mais rejette le vainqueur sincère tout en bas, pour le faire perdre au profit d’un rival plus proche.',
    coalitionLabel: 'Taille de la coalition : {{pct}} % de l’électorat',
    coalitionHint:
      'Un seul électeur pèse rarement. Plus le bloc coordonné est grand, plus le vote stratégique peut renverser le résultat — c’est le « coût » de la manipulation.',
    outcomeFlipPre: 'Le vote stratégique fait basculer le vainqueur :',
    outcomeHoldPre: 'Le vainqueur tient malgré le vote stratégique :',
    outcomeHoldPost: 'reste élu.',
    outcomeDefect: '{{pct}} % des électeurs abandonnent leur favori pour le vote utile.',
    leaderOnly: 'L’analyse stratégique détaillée est disponible en mode Dirigeant.',
    sincereTitle: '🗳️ Vote sincère ou vote utile ?',
    sincereHint:
      'Votre conviction, méthode par méthode — glissez le losange « Vous » sur la carte.',
    vulnTitle: '⚡ Vulnérabilité stratégique (Gibbard–Satterthwaite)',
    vulnSub: 'à la demande · lent',
    equilibriumTitle: '♟ Équilibre stratégique (jeu itéré)',
    equilibriumSub: 'à la demande · tous les camps jouent',
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
    blankTitle: 'Vote blanc (en direct)',
    blankToggle: 'Activer le vote blanc',
    blankHint:
      'Les électeurs trop loin de tous les candidats déposent un bulletin vide au lieu de voter pour l’un d’eux.',
    blankLensLabel: 'Régime constitutionnel',
    blankRate: '{{count}} électeurs sur le total ont voté blanc ({{pct}} %).',
    blankLabNote:
      'Pour composer un résultat à la main et comparer les quatre régimes → fiche Vote blanc du Laboratoire.',
    svIntro:
      'Part des électeurs qui pourraient améliorer leur résultat en votant insincèrement (Gibbard–Satterthwaite, par force brute). Plus c’est bas, plus la méthode résiste. Calcul lourd — à la demande, hors lecture temps-réel.',
    svComputing: 'Calcul… (quelques secondes)',
    svRun: '▶ Calculer la vulnérabilité stratégique',
    svError: 'Calcul indisponible (backend). Réessayez après redémarrage.',
    svFooter: 'Barre = part d’électeurs avec un mensonge profitable (0 % = aucun n’y gagne).',
    svColManip: 'Manipulable',
    svColNoShow: 'No-show',
    svColLnh: 'LNH',
    svNoShowYes: 'Paradoxe du non-vote détecté sur cet électorat',
    svNoShowNo: 'Aucun paradoxe du non-vote sur cet électorat',
    svLnhOk: 'Satisfait Later-No-Harm : cacher ses derniers choix ne nuit jamais',
    svLnhFail: 'Viole Later-No-Harm : classer un candidat en bas peut le faire gagner',
    svAxiomFooter:
      'No-show = calculé en direct sur CET électorat (une coalition gagnerait à s’abstenir). LNH = propriété connue de la méthode, invariante.',
  },
  vse: {
    title: 'Le coût du vote stratégique (VSE)',
    subtitle:
      'Combien de bien-être chaque méthode gaspille quand les électeurs cessent d’être sincères',
    intro:
      'Efficacité de satisfaction des électeurs (VSE, Quinn 2017, d’après Merrill 1984) : 1 = la méthode élit le candidat qui maximise le bien-être, 0 = elle ne fait pas mieux qu’un tirage au sort, négatif = elle fait pire. On fait varier la part d’électeurs qui votent « utile ».',
    aria: 'Courbes de VSE par méthode selon la part d’électeurs stratégiques',
    xAxis: 'Part d’électeurs stratégiques',
    best: 'optimum',
    random: 'hasard',
    need2: 'Il faut au moins deux candidats pour mesurer le bien-être.',
    readout:
      'Chaque courbe = une méthode. Le chiffre dans la légende est le bien-être perdu entre un électorat sincère et un électorat entièrement stratégique. Survolez une méthode pour l’isoler.',
    flat: 'Sur cet électorat, toutes les méthodes élisent déjà le même candidat — le meilleur — et la stratégie n’y change rien. C’est un vrai résultat, pas un bug : essayez un électorat polarisé (Électorat → Composer) ou un candidat centriste pris en étau pour voir la stratégie mordre.',
    convention:
      'Convention affichée : un électeur « stratégique » applique la compression de Duverger — il repère les deux favoris dans les premiers choix sincères (c’est le sondage), place celui qu’il préfère en tête et l’autre en dernier. L’utilité est toujours lue sur ses préférences RÉELLES : il ment sur son bulletin, jamais sur ce qu’il veut. Bandes = p10–p90 sur des ré-échantillons de l’électorat.',
  },
  parliament: {
    mirror: {
      left_lib: 'Gauche · libéral',
      left_cons: 'Gauche · conservateur',
      right_lib: 'Droite · libéral',
      right_cons: 'Droite · conservateur',
    },
    unavailable:
      '⚠ Hémicycle indisponible : le calcul de l’assemblée n’a pas abouti. Si vous venez de mettre à jour, redémarrez le serveur backend (uvicorn) pour qu’il prenne le nouveau schéma.',
    mapAria: 'Carte idéologique — partis et territoires',
    hemicycleAria: 'Hémicycle — sièges par parti',
    seatsLine: '{{seats}} sièges · majorité {{majority}}',
    computing: 'Calcul de l’assemblée…',
    awaiting: '{{seats}} sièges — en attente de la répartition',
    gallagherTitle: 'Indice de Gallagher — 0 = parfaitement proportionnel',
    disproportion: 'Disproportion',
    effPartiesTitle: 'Nombre effectif de partis (sièges)',
    effParties: 'Partis effectifs',
    wastedTitle: 'Part des voix sans représentation',
    wasted: 'Voix gaspillées',
    coalitionToggleTitle: 'Cliquer pour ajouter/retirer de la coalition',
    votesSeatsNote: 'Barre claire = voix, barre pleine = sièges. ✕ = exclu par le seuil.',
    congruenceTitle:
      'Distance entre la position du corps élu (pondérée par sièges) et l’électeur médian — sur la carte : ✚ médiane, ● assemblée, ◆ coalition gouvernante.',
    congruenceHead: 'Congruence (✚ médiane · ● assemblée · ◆ gouvernement)',
    gapLine: 'Écart assemblée–médiane :',
    governingCoalition: 'coalition gouvernante :',
    mirrorTitle:
      'L’assemblée ressemble-t-elle à l’électorat, région idéologique par région ? (Représentation descriptive sur l’espace modélisé — aucune démographie n’est inventée.)',
    mirrorHead: 'Miroir descriptif (régions idéologiques)',
    mirrorNote: 'Barre grise = électorat, barre pleine = sièges.',
    coalitionEmpty:
      'Cliquez sur des partis pour assembler une coalition majoritaire ({{majority}} sièges).',
    coalitionLabel: 'Coalition :',
    seatsWord: 'sièges',
    coalitionMajority: ' — majorité ✔',
    coalitionNoMajority: ' — pas de majorité',
    coalitionSpan: ' · étendue idéologique {{span}}',
  },
  noshow: {
    title: '🚷 Paradoxe du non-votant (exemple — scrutin à deux tours)',
    intro:
      '34 électeurs, 3 candidats. Les partisans de C les classent C ▸ A ▸ B. Faites-en abstenir quelques-uns : observez le vainqueur.',
    abstainers: 'Partisans de C qui s’abstiennent : {{n}}',
    winner: 'Vainqueur :',
    paradox:
      ' — Paradoxe ! En s’abstenant, les partisans de C font élire {{winner}} (leur choix nº {{rank}}), qu’ils préfèrent à {{base}} (leur choix nº {{baseRank}}/dernier). Leur participation leur nuisait.',
    noFlip: ' — avec tous les votants, c’est le 3ᵉ choix des partisans de C qui l’emporte.',
  },
  bilan: {
    evaluatedFor: 'Évalué pour :',
    sensibility: 'Votre sensibilité',
    fineTune: 'Réglage fin…',
    simpleDial: '← Cadran simple',
    majoritarian: 'Majoritaire (décisif)',
    consensualist: 'Consensualiste (inclusif)',
    bandNote: '{{count}} ré-échantillonnages',
    labCtaNote: 'Paradoxes, théorie, mécanismes, dynamiques temporelles…',
    labCta: '→ Approfondir dans le Laboratoire',
    tableTitle: 'Résultats par méthode',
    colMethod: 'Méthode',
    colWinner: 'Vainqueur',
    colStability: 'Stabilité',
    colStrategy: 'Stratégie',
    colCondorcet: 'Condorcet',
    verdictTitle: 'Le verdict',
    verdictSplit: '{{count}} vainqueurs différents selon la méthode',
    verdictSplitSub: 'Le choix de la règle change l’issue — c’est toute la question.',
    verdictConsensus: '{{name}} l’emporte, quelle que soit la méthode',
    verdictConsensusSub: 'Rare consensus : ici, le choix de la méthode ne change rien.',
    condorcetIs: 'Vainqueur de Condorcet : {{name}} — il bat chaque rival en duel.',
    condorcetNone: 'Aucun vainqueur de Condorcet : les duels forment un cycle.',
    winnersTitle: 'Qui gagne, et avec quelles méthodes',
    methodCountOne: '1 méthode',
    methodCountMany: '{{count}} méthodes',
    condorcetBadge: 'Condorcet',
    robustnessTitle: 'Robustesse de chaque verdict',
    robustnessSub: 'Trois axes de résistance, sur {{count}} ré-échantillons de l’électorat.',
    robustnessLegend:
      'Chaque score va de 0 à 100 (plus haut = plus robuste) ; la barre pâle = fourchette sur {{count}} ré-échantillons de l’électorat, le trait = valeur moyenne.',
  },
  replay: {
    title: 'Comment ça marche : {{method}}',
    methodLabel: 'Méthode',
    groupCompared: 'Méthodes comparées',
    groupExtra: 'À découvrir',
    sampleNote: 'sur {{count}} électeurs tirés au hasard',
    step: '{{i}} / {{n}}',
    winner: 'Vainqueur :',
    play: 'Lire',
    pause: 'Pause',
    restart: 'Rejouer',
    reshuffle: 'Nouveau tirage',
    speed: 'Vitesse',
    speed_calm: 'Lent',
    speed_normal: 'Normal',
    speed_fast: 'Rapide',
    tie: 'Égalité parfaite — aucun vainqueur départagé.',
    family: {
      count:
        'On compte les bulletins un par un : chaque barre monte à mesure que les voix tombent.',
      elim: 'Tour par tour, on élimine un candidat et on redistribue ses voix.',
      pairwise: 'Duel par duel : chaque candidat en affronte un autre, on compte les duels gagnés.',
      twophase:
        'Deux temps : on additionne les notes, puis une finale départage les deux meilleurs.',
      lottery: 'Un seul bulletin est tiré au sort : son premier choix l’emporte.',
    },
    unit: {
      votes: 'voix',
      points: 'points',
      duels: 'duels gagnés',
      grade: 'note médiane (0–5)',
    },
    count: {
      start: 'Aucune voix comptée. Chaque électeur va déposer son bulletin.',
      plurality: 'Électeur {{n}} vote pour son 1ᵉʳ choix : {{cand}}.',
      borda:
        'Électeur {{n}} classe les candidats (1ᵉʳ : {{cand}}) → des points à chacun selon le rang.',
      approval: 'Électeur {{n}} approuve : {{cand}}.',
      score: 'Électeur {{n}} attribue une note à chaque candidat (préféré : {{cand}}).',
      antiPlurality:
        'Électeur {{n}} vote contre son pire choix ({{cand}}) : tous les autres marquent 1.',
      dowdall: 'Électeur {{n}} classe les candidats (1ᵉʳ : {{cand}}) → 1, ½, ⅓… selon le rang.',
      cumulative: 'Électeur {{n}} répartit son point entre les candidats (surtout {{cand}}).',
      maximin:
        'Électeur {{n}} : on retient sa pire note ({{cand}}) — la barre ne peut que baisser.',
      nash: 'Électeur {{n}} : on multiplie les notes (moyenne géométrique) — une note nulle écrase tout.',
      done: '{{cand}} a le plus de voix : élu.',
    },
    elim: {
      tr1: '1ᵉʳ tour : on compte les 1ᵉʳˢ choix de tout le monde.',
      trRunoff: 'Personne n’a la majorité : 2ᵈ tour entre {{a}} et {{b}}.',
      majority: 'Tour {{round}} : {{cand}} dépasse 50 % — élu.',
      irvRound:
        'Tour {{round}} : {{cand}} a le moins de 1ᵉʳˢ choix → éliminé, ses voix se reportent.',
      coombsRound: 'Tour {{round}} : {{cand}} est le plus souvent classé dernier → éliminé.',
      nansonRound: 'Tour {{round}} : score de Borda sous la moyenne → éliminé : {{cand}}.',
      baldwinRound: 'Tour {{round}} : plus faible score de Borda → éliminé : {{cand}}.',
      bucklinRound:
        'Rang {{round}} : on ajoute les choix de rang {{round}}, personne n’a encore la majorité.',
      bucklinMajority: 'Rang {{round}} : {{cand}} dépasse 50 % des mentions — élu.',
      done: '{{cand}} est le dernier en lice : élu.',
    },
    pairwise: {
      start: 'On fait s’affronter chaque paire de candidats en duel direct.',
      duel: '{{a}} vs {{b}} : {{av}}–{{bv}} → {{cand}} gagne le duel.',
      doneCopeland: '{{cand}} gagne le plus de duels (Copeland) : élu.',
      doneMinimax: 'Minimax : {{cand}} a la plus petite pire défaite — élu.',
      doneSchulze: 'Schulze : {{cand}} l’emporte par les plus forts chemins de battage — élu.',
      doneRankedPairs:
        'Paires ordonnées : on verrouille les duels les plus nets, {{cand}} est en tête — élu.',
      doneBlack: 'Black : vainqueur de Condorcet s’il existe, sinon Borda tranche → {{cand}}.',
      doneSplitCycle:
        'Split Cycle : on écarte la défaite la plus faible de chaque cycle → {{cand}}.',
      doneKemeny:
        'Kemeny-Young : le classement le plus « d’accord » avec tous les bulletins place {{cand}} en tête.',
      doneRiver:
        'River : comme les paires ordonnées, mais un seul verrou entrant par candidat → {{cand}}.',
    },
    benham: {
      cw: 'Tour {{round}} : {{cand}} bat tous les rivaux restants (Condorcet) — élu.',
      round:
        'Tour {{round}} : pas de vainqueur de Condorcet → on élimine le plus faible ({{cand}}).',
    },
    raynaud: {
      round:
        'Tour {{round}} : la pire défaite est {{a}} bat {{b}} ({{av}}–{{bv}}) → {{b}} éliminé.',
    },
    smith: {
      set: 'On garde le « Smith set » — le plus petit groupe qui bat tous les autres : {{cand}}.',
      irv: 'Tour {{round}} : dans ce groupe, on élimine le plus faible en 1ᵉʳˢ choix ({{cand}}).',
    },
    phase: {
      starScores: 'Phase 1 — on additionne les notes de chaque candidat.',
      starRunoff: 'Phase 2 — finale : {{a}} contre {{b}}, chaque électeur préfère l’un des deux.',
      mjMedian: 'On classe chaque candidat par sa note médiane.',
      done: '{{cand}} l’emporte.',
    },
    lottery: {
      shares: 'Chaque candidat a une part proportionnelle à ses 1ᵉʳˢ choix.',
      draw: 'Un bulletin est tiré au hasard → {{cand}} (résultat le plus probable).',
    },
  },
  realElection: {
    title: '🗳 Épreuve du réel : de vrais scrutins',
    sub: 'mêmes bulletins, méthodes différentes — scrutins réels et figés (Burlington 2009, Alaska 2022), sans rapport avec l’électorat que vous configurez sur la carte',
    pick: 'Scrutin',
    headlinePre: 'Sur les mêmes bulletins,',
    headlineEnd: 'vainqueurs différents selon la seule méthode.',
    note: 'Bulletins classés authentiques (Burlington : PrefLib 00005 ; Alaska : Graham-Squire & McCune, arXiv:2303.00108, tab. 4 — la répartition publiée des bulletins du cast vote record de l’État). On ne tabule que les méthodes sans ambiguïté sur des bulletins tronqués (pluralité, deux tours, IRV, famille de Condorcet) ; Borda et les méthodes par note exigent une convention que les bulletins ne fournissent pas. Détails : duels gagnés (Condorcet), pire marge de défaite (minimax).',
  },
  approvalExperiment: {
    title: 'Et avec un autre bulletin ? Le vote par approbation (2017)',
    sub: 'Même scrutin, même électorat — un bulletin d’approbation au lieu d’un seul nom. Le vainqueur tient (Macron), mais l’ordre s’effondre : Le Pen passe 2ᵉ → 5ᵉ, Mélenchon 4ᵉ → 2ᵉ. L’approbation aurait envoyé Macron au second tour face à Mélenchon, pas à Le Pen.',
    colApproval: 'Approbation',
    colOfficial: '1er tour',
    caveat:
      'Expérimentation « Voter Autrement » in situ, 1er tour 2017 : 3 894 bulletins d’approbation dans 5 communes, échantillon auto-sélectionné puis extrapolé à la France. Un taux d’approbation (on peut approuver plusieurs candidats — 2,48 en moyenne) n’est pas une part de voix : les deux colonnes se comparent par leur ordre, pas par leurs totaux.',
    source:
      'Approbation : Baujard et al. (rangevoting.org/France2017). Officiel : Ministère de l’Intérieur.',
  },
  lexique: {
    title: '📖 Lexique',
    intro: 'Chaque notion en une phrase simple — et un lien pour la voir à l’œuvre.',
    search: 'Chercher un terme…',
    seeInAction: 'Voir en action',
    empty: 'Aucun terme ne correspond.',
    count: '{{n}} termes',
  },
  blankVote: {
    title: '⬜ Vote blanc — et après ?',
    act1Kicker: '1 — On peut voter blanc',
    act1Title: 'Trois silences, pas un seul',
    act1Lede:
      'Ne pas choisir n’est pas une seule chose. Trois gestes très différents se cachent derrière « je n’ai pas voté pour un candidat ».',
    silences: {
      abstention: {
        term: 'Abstention',
        desc: 'On ne se déplace pas, on ne dépose rien. Le bulletin n’existe pas — il sort du décompte.',
      },
      blanc: {
        term: 'Vote blanc',
        desc: 'On se déplace et on dépose une enveloppe vide. Un choix exprimé : « aucun de ceux-là », mais je suis là.',
      },
      nul: {
        term: 'Vote nul',
        desc: 'Bulletin raturé, déchiré, non conforme. Souvent une erreur, parfois une colère — mais juridiquement invalide.',
      },
    },
    act2Kicker: '2 — On en fait quoi ?',
    act2Title: 'Le blanc l’emporte. Et maintenant ?',
    act2Lede:
      'Construis un résultat, pousse le blanc jusqu’à ce qu’il domine, et regarde : le même vote connaît quatre destins selon la règle de comptage. Aucun n’est « le bon » — c’est la question.',
    mixerTitle: 'Compose le résultat',
    presets: {
      balanced: 'Équilibré',
      blankLeads: 'Blanc en tête',
      blankMajority: 'Blanc majoritaire',
    },
    blankLabel: 'Blanc',
    redoBadge: 'On recommence',
    electedBadge: 'Élu',
    lens: {
      france_today: {
        label: 'Aujourd’hui en France (hors exprimés)',
        mechanism:
          'Depuis 2014, le blanc est compté et publié, mais retiré des suffrages exprimés : il ne pèse sur aucun seuil.',
      },
      in_exprimes: {
        label: 'Si le blanc comptait (réforme)',
        mechanism:
          'On l’intègre aux exprimés : le dénominateur gonfle, et la barre des 50 % devient plus dure à franchir.',
      },
      competitive: {
        label: 'Compétitif (Uruguay)',
        mechanism:
          'Le blanc est traité comme un candidat : s’il devance le premier, la candidature est rouverte.',
      },
      threshold: {
        label: 'Seuil 50 % (Colombie)',
        mechanism:
          'Si le blanc dépasse la moitié des voix, l’élection est annulée et rejouée avec de nouveaux candidats.',
      },
    },
    outcome: {
      elected: '{{winner}} est élu — {{pct}} des exprimés.',
      no_majority: '{{winner}} en tête à {{pct}}, mais sous la majorité : pas de mandat clair.',
      blank_wins: 'Le blanc devance tout le monde ({{pct}}) : on rouvre la campagne.',
      annulled: 'Blanc majoritaire ({{pct}}) : l’élection est annulée.',
    },
    reflectTitle: 'À toi de trancher',
    reflectQ1:
      'Un vote blanc massif, c’est un mandat pour recommencer, ou une abdication qui laisse les autres décider ?',
    reflectQ2:
      'Si le blanc pouvait bloquer une élection, jusqu’où : un second tour, une annulation, de nouveaux candidats ?',
    reflectQ3: 'Et le risque de blocage sans fin — vaut-il la reconnaissance d’un refus légitime ?',
    worldKicker: 'Ce qui existe déjà',
    worldTitle: 'Comment le monde répond',
    worldLede:
      'Seize pays, seize réponses à la même question. Les deux marqués d’un point (Uruguay, Colombie) laissent réellement le blanc changer l’issue.',
    col: {
      country: 'Pays',
      status: 'Statut du blanc',
      rate: 'Taux moyen',
      impact: 'Effet',
    },
    status: {
      counted_separate: 'Compté à part',
      symbolic: 'Symbolique',
      competitive: 'Compétitif',
      threshold: 'Seuil déclencheur',
      merged_invalid: 'Fondu dans les nuls',
    },
    impactYes: 'Peut modifier ou annuler l’élection',
    impactNo: 'Aucun effet sur le résultat',
    source: 'Sources : législations électorales nationales (voir data/blankVoteRegimes).',
  },
  atlas: {
    kicker: 'Atlas',
    title: '🌍 Atlas des régimes électoraux',
    intro:
      'Un globe qui tourne : chaque démocratie à sa place, colorée par sa méthode de vote — ou par ce qu’elle fait du vote blanc. Fais-le tourner, ou attrape-le pour l’orienter, puis clique un pays.',
    colorBy: 'Colorer par :',
    byMethod: 'Méthode',
    byBlank: 'Vote blanc',
    dragHint: 'Clique un point pour voir le régime du pays.',
    methodLabel: 'Méthode :',
    blankLabel: 'Vote blanc :',
    unknownBlank: 'Non renseigné',
    source: 'Sources : législations électorales nationales (voir lib/electoralAtlas).',
    method: {
      fptp: 'Scrutin majoritaire à un tour (FPTP)',
      two_round: 'Scrutin à deux tours',
      irv: 'Vote alternatif (IRV)',
      stv: 'Vote unique transférable (STV)',
      mmp: 'Proportionnelle mixte (MMP)',
      party_list_pr: 'Proportionnelle de liste',
      mixed: 'Système mixte (parallèle)',
    },
  },
  curiosity: {
    kicker: 'Par curiosité',
    title: 'Par où commencer ? Suis ta question.',
    sub: 'Chaque question ouvre l’histoire qui y répond, dans l’instrument.',
    q: {
      wasted: 'Pourquoi dit-on que mon vote « ne sert à rien » ?',
      spoiler: 'Comment un candidat sans aucune chance peut-il faire perdre mon favori ?',
      centre: 'Le candidat que presque tout le monde accepte peut-il être éliminé ?',
      method: 'La méthode de dépouillement peut-elle changer le vainqueur ?',
      best: 'Le mieux placé est-il vraiment le meilleur pour tous ?',
      small: 'Un petit parti peut-il être effacé par une simple barre ?',
    },
  },
  explain: {
    kicker: 'Pourquoi ce gagnant ?',
    count:
      '{{winner}} l’emporte sur le plus haut total : {{winnerVal}} contre {{runnerUpVal}} pour {{runnerUp}}.',
    elim: '{{winner}} gagne aux reports : à mesure que les moins bien placés sont éliminés, leurs voix se reportent, et {{winner}} finit devant {{runnerUp}} ({{winnerVal}} à {{runnerUpVal}}).',
    pairwise:
      '{{winner}} gagne tous ses duels : c’est le candidat que la majorité préfère face à chaque rival, un contre un.',
    twophase:
      '{{winner}} l’emporte au second tour : des deux finalistes, il devance {{runnerUp}} ({{winnerVal}} à {{runnerUpVal}}).',
    lottery:
      '{{winner}} est tiré au sort : la probabilité de chacun était proportionnelle à ses soutiens.',
  },
  scorecard: {
    drillTitle: 'Approfondir dans le Lab',
    drillAria: 'Approfondir « {{label}} » dans le Lab',
    bandFooter: 'Bande = p10–p90 sur {{note}} ; trait = moyenne.',
  },
  composer: {
    sample: 'Échantillon',
    numVoters: 'Nombre d’électeurs : {{n}}',
    seed: 'Graine : {{seed}}',
    rerollTitle: 'Tire un nouvel électorat (mêmes réglages, autre échantillon).',
    reroll: '🎲 Re-tirer',
    ideoTitle:
      'Forme du nuage gaussien en mode simple (le mode composé la remplace par les communautés).',
    ideoLabel: 'Idéologie (mode simple)',
    ideoRandom: 'Aléatoire (large)',
    ideoCentrist: 'Centriste (resserré)',
    ideoPolarized: 'Polarisé (deux camps)',
    modeSimple: 'Simple (gaussien)',
    modeComposed: 'Composé (communautés)',
    hintComposed: 'Mélange de blocs — édite chaque communauté ci-dessous.',
    hintSimple: 'Nuage idéologique unique (réglage « idéologie »).',
    models: 'Modèle',
    modelsPlaceholder: '— Choisir un modèle —',
    corrTitle: 'Couple l’axe sociétal à l’axe économique.',
    corr: 'Corrélation des axes : {{val}}',
    noiseTitle:
      'Flou de mesure global ajouté à toutes les positions — l’incertitude d’un sondage, distincte de la dispersion réelle des blocs.',
    noise: 'Bruit de mesure (sondage) : {{pct}} %',
    colCommunity: 'Communauté',
    colEcon: 'Écon. (x)',
    colSocial: 'Sociétal (y)',
    colSpread: 'Dispersion',
    colSize: 'Taille',
    removeTitle: 'Retirer',
    turnoutRow: '{{label}} · participation',
    zRow: '{{label}} · 3ᵉ axe (z)',
    addCommunity: '+ Ajouter une communauté',
    ioSummary: 'Données d’entrée — importer / exporter (JSON)',
    import: 'Importer',
    copied: 'Copié ✓',
    export: 'Exporter (copier)',
    jsonError: 'JSON invalide (il faut un tableau « communities » non vide).',
    footer:
      'L’électorat composé alimente la vue dirigeant (carte, zones, bilan, coloré par communauté), le parlement (sièges, bilan d’assemblée) et le taux de paradoxe (vrai taux de cycle spatial, ré-échantillonné). Le 3ᵉ axe n’agit qu’en mode carte 3D ; le bruit de mesure simule l’incertitude d’un sondage.',
  },
  sincerity: {
    typeCompromise: 'vote utile (compromis)',
    typeBurying: 'enterrement d’un rival',
    intro:
      'Vous êtes un électeur. Votre voix seule pèse peu — la tentation de voter « utile » est collective, alors réglez la taille de votre bloc de conviction. Pour chaque méthode : voter sincèrement est-il votre meilleure réponse, ou la méthode vous pousse-t-elle à trahir votre favori ?',
    posEcon: 'Votre position (axe écon.) : {{val}}',
    posSocial: 'Votre position (axe sociétal) : {{val}}',
    posZ: 'Votre position (axe z) : {{val}}',
    sincereOrder: 'Votre ordre sincère :',
    tip: 'Astuce : glissez le marqueur',
    tipMarker: '◆ Vous',
    tipEnd: 'directement sur la carte.',
    blocTitle:
      'Nombre d’électeurs qui partagent votre conviction et voteraient comme vous — votre levier collectif.',
    blocLabel: 'Électeurs comme vous : {{n}}',
    headlinePre: 'À votre place,',
    headlineMid: '/15 méthodes récompensent la conviction ;',
    headlineEnd: 'vous poussent au vote stratégique.',
    temptingHead: '⚠ Vous seriez tenté de trahir votre favori',
    temptSincere: 'sincère → {{winner}} ; mais votez',
    safeHead: '✓ Voter sincèrement est votre meilleure réponse',
    elects: 'Élit {{winner}}',
    scanTitle:
      'Échantillonne de vrais électeurs de cet électorat et mesure, par méthode, à quelle fréquence ils seraient tentés de voter stratégiquement.',
    scanRescan: '↻ Re-balayer l’électorat',
    scanRun: '▶ Balayer l’électorat (toutes méthodes)',
    scanHeadPre: 'Sur {{sampled}} électeurs, la méthode qui minimise le vote utile :',
    scanHeadEnd: '({{pct}} %).',
    scanFooter:
      'Barre = part d’électeurs tentés de trahir leur conviction (plus court = méthode plus sincère sur cet électorat).',
    note: 'Contrainte centrale du projet : voter par conviction, jamais par élimination. On teste les stratégies classiques (compromis « vote utile » et enterrement d’un rival) ; l’absence de tentation ici ne prouve pas l’infaillibilité, mais signale une méthode robuste pour cet électorat.',
  },
  equilibrium: {
    intro:
      'Et si TOUS les camps votaient stratégiquement ? On rejoue les déviations en chaîne (chaque bloc répond à la situation) jusqu’à ce que les bulletins se stabilisent. Le vainqueur sincère survit-il au jeu stratégique, ou la méthode bascule-t-elle sur un autre ?',
    runTitle:
      'Joue la meilleure réponse itérée depuis un électorat sincère, pour chaque méthode, jusqu’à un équilibre (ou un cycle).',
    run: '▶ Simuler le jeu stratégique (toutes méthodes)',
    rerun: '↻ Rejouer',
    headlinePre: 'Sous jeu stratégique,',
    headlineEnd: 'méthodes changent de vainqueur ({{groups}} blocs de préférence).',
    shiftedHead: '⚠ La stratégie déplace le vainqueur',
    afterPasses: '(après {{n}} tours)',
    cycleHead: '∞ Aucun équilibre (le jeu cycle)',
    cycleTitle: 'Les bulletins ne se stabilisent pas : pas d’équilibre pur sous ces dynamiques.',
    stableHead: '✓ Le vainqueur sincère résiste',
    elects: 'Élit {{winner}}, avant comme après stratégie',
    note: 'Meilleure réponse itérée (« iterative voting », Meir et al.), mêmes stratégies que ci-dessus (compromis, enterrement). Un vainqueur qui se déplace ou un cycle signale une méthode fragile au jeu stratégique sur cet électorat ; convention, pas théorème.',
  },
  structural: {
    title: '⚖ Équités structurelles',
    malTitle: '0 = circonscriptions de population égale ; 1 = fortement inégales (≈ 4:1).',
    mal: 'Malapportionnement',
    analyze: '▶ Analyser',
    intro:
      'Les règles autour de la règle : taille des circonscriptions, découpage, pondération des conseils, scrutin plurinominal — chacune déplace le pouvoir sans toucher au mode de scrutin.',
    unequalWeight: 'Poids inégal des voix',
    popPerSeat: 'Population par siège : rapport',
    controlShare: 'Part des voix pouvant contrôler la majorité des sièges :',
    vsEqual: '(vs {{pct}} % à circonscriptions égales)',
    egTitle:
      '(voix gaspillées A − voix gaspillées B) / total bipartite — la métrique standard du charcutage. Gaspillé = voix perdantes + surplus au-delà de 50 % + 1.',
    egLabel: 'Efficiency gap ({{a}} vs {{b}})',
    disfavors: '{{pct}} % — défavorise',
    penroseTitle:
      'Pondérer les délégués par √population égalise l’influence des citoyens (approximation de Penrose) ; les pondérations égale ou proportionnelle la déséquilibrent.',
    penroseHead: 'Conseil — loi de Penrose (√)',
    schemeEqual: '1 circonscription = 1 voix',
    schemeProp: 'Poids ∝ population',
    schemePenrose: 'Poids ∝ √population',
    citizenPower: 'pouvoir citoyen max/min :',
    cumTitle:
      'M sièges dans une circonscription unique : en vote en bloc, le parti en tête rafle tout ; en vote cumulatif, une minorité cohésive concentre ses voix et obtient des sièges.',
    cumHead: 'Plurinominal : bloc vs cumulatif ({{seats}} sièges)',
    bloc: 'Bloc',
    cumulative: 'Cumulatif',
    minorityLead: 'Sièges des minorités :',
    blocSuffix: '(bloc) →',
    cumSuffix: '(cumulatif)',
  },
  issues: {
    yes: 'Oui',
    no: 'Non',
    title: '🗳 Enjeux & groupage (Ostrogorski)',
    issuesLabel: 'Enjeux',
    analyze: '▶ Analyser',
    demoTitle:
      'Le profil construit canonique : le programme gagnant est désavoué enjeu par enjeu par la majorité.',
    demo: 'Paradoxe construit',
    intro:
      'Élire un programme groupe les enjeux ; les majorités enjeu par enjeu peuvent dire l’inverse. Mode spatial : chaque enjeu est une ligne de partage du plan (convention déclarée, même graine = mêmes enjeux).',
    paradoxPrefix: '⚠ Paradoxe d’Ostrogorski : ',
    divergeOn_one:
      'remporte le vote par programme, mais la majorité le désavoue sur {{count}}/{{num}} enjeu.',
    divergeOn_other:
      'remporte le vote par programme, mais la majorité le désavoue sur {{count}}/{{num}} enjeux.',
    yesShare: 'Oui (part)',
    majorityCol: 'Majorité enjeu',
    platformCol: 'Programme élu',
  },
  democracy: {
    title: 'Carte des démocraties (axe de Lijphart)',
    aria: 'Axe majoritaire–consensus',
    majoritarian: '← Majoritaire (décisif, winner-take-all)',
    consensus: 'Consensus (proportionnel, partage) →',
    footer:
      'Pays : scores « exécutifs-partis » approximatifs (Lijphart 2012), pour situer. Vos structures sont positionnées en direct : moyenne de proportionnalité, pluralisme, minorités et (1 − gouvernabilité) sur l’électorat courant — convention déclarée, 1 seule dimension (le fédéralisme n’est pas modélisé).',
  },
  values: {
    weightsTitle: 'Vos pondérations',
    dominated: 'écarté (dominé)',
    spotlight: 'selon vos pondérations',
    onFrontier: 'sur la frontière',
    footer:
      'Les options dominées sont écartées — un fait objectif. Entre celles qui restent, il n’existe pas de « meilleur » système : vos curseurs ne font qu’éclairer un point de la frontière, et pondérer est déjà un choix de valeurs.',
  },
  campaign: {
    emptyPrompt:
      'Composez d’abord un électorat dans le moment ① Électorat, puis revenez lancer une campagne.',
  },
  nonspatial: {
    computing: 'Calcul du profil…',
    aria: 'Biplot du profil non-spatial : électeurs et candidats projetés dans un plan.',
    winnerPre: 'Vainqueur sur ce profil :',
    noWinner: 'Aucun vainqueur départagé (cycle ou égalité).',
    caption:
      'Positions déduites des bulletins (projection PCA), non choisies : les candidats ne sont pas déplaçables. Chaque candidat est placé au barycentre des électeurs qui le soutiennent.',
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
    shakeCI: 'IC 95 % : {{lo}}–{{hi}} %',
    shakeCITitle: 'Intervalle de confiance à 95 % (Wilson) : {{lo}}–{{hi}} %',
    shakeCIFooter:
      'Barre pleine = estimation ; voile = intervalle de confiance à 95 % (Wilson, n = {{n}}). Plus de tirages = intervalle plus serré.',
    democracyTitle: '🗺 Carte des démocraties (Lijphart)',
    democracySub: 'majoritaire ↔ consensus',
    democracyComputing: 'Calcul en cours…',
    issuesTitle: '🗳 Enjeux & groupage (Ostrogorski)',
    structuralTitle: '⚖ Équités structurelles',
  },
  rules: {
    plurality: 'Pluralité (1 tour)',
    two_round: 'Deux tours',
    irv: 'Vote alternatif (IRV)',
    borda: 'Borda',
    approval: 'Approbation',
    condorcet: 'Condorcet (Copeland)',
    minimax: 'Condorcet (minimax)',
    schulze: 'Condorcet (Schulze)',
    bucklin: 'Bucklin',
    coombs: 'Coombs',
    nanson: 'Nanson',
    baldwin: 'Baldwin',
    ranked_pairs: 'Condorcet (paires ordonnées)',
    random_ballot: 'Vote au sort (loterie)',
    star: 'STAR',
    majority_judgment: 'Jugement majoritaire',
    score: 'Note (score)',
    anti_plurality: 'Anti-pluralité (véto)',
    dowdall: 'Dowdall (Nauru)',
    black: 'Black (Condorcet-Borda)',
    smith_irv: 'Smith-IRV (Tideman)',
    split_cycle: 'Split Cycle',
    kemeny: 'Kemeny-Young',
    cumulative: 'Vote cumulatif',
    maximin: 'Maximin (utilité)',
    benham: 'Benham (Condorcet-IRV)',
    river: 'River',
    nash: 'Nash (produit d’utilités)',
    raynaud: 'Raynaud',
  },
  // Plain-language method labels (mode « sans jargon »). Bounded to the methods a
  // newcomer actually meets; anything absent falls back to its technical name.
  rulesPlain: {
    plurality: 'Le plus de voix',
    two_round: 'À deux tours',
    irv: 'Élimination par tours',
    coombs: 'Élimination du plus rejeté',
    borda: 'Points par rang',
    condorcet: 'Le préféré en duel',
    approval: 'Cocher qui convient',
    score: 'Notes moyennes',
    star: 'Notes, puis duel',
    cumulative: 'Points à répartir',
  },
  structures: {
    pr: 'Proportionnelle (listes)',
    fptp: 'Circonscriptions (FPTP)',
    mmp: 'Mixte (MMP)',
  },
  axes: {
    condorcet_efficiency: {
      label: 'Efficacité Condorcet',
      hint: "Part des ré-échantillonnages (avec vainqueur de Condorcet) où la règle l'élit.",
    },
    strategic_resistance: {
      label: 'Résistance stratégique',
      hint: 'Le vainqueur survit-il à une compression stratégique vers les deux favoris ? (heuristique documentée)',
    },
    welfare: {
      label: 'Bien-être (regret)',
      hint: '1 − regret bayésien normalisé du vainqueur (utilité = −distance).',
    },
    majority_satisfaction: {
      label: 'Satisfaction majoritaire',
      hint: 'Part des électeurs pour qui le vainqueur vaut au moins leur candidat médian.',
    },
    simplicity: {
      label: 'Simplicité',
      hint: 'Convention déclarée : complexité du bulletin et du dépouillement (sans bande).',
    },
    stability: {
      label: 'Stabilité',
      hint: 'Part des ré-échantillonnages élisant le vainqueur modal.',
    },
    proportionality: {
      label: 'Proportionnalité',
      hint: '1 − indice de Gallagher (normalisé).',
    },
    pluralism: {
      label: 'Pluralisme (diversité)',
      hint: 'Part de la diversité des voix (NEP) qui survit en sièges.',
    },
    effective_votes: {
      label: 'Voix utiles',
      hint: '1 − part des voix gaspillées.',
    },
    minority_representation: {
      label: 'Représentation des minorités',
      hint: 'Partis ≥ 3 % des voix détenant au moins un siège.',
    },
    governability: {
      label: 'Gouvernabilité',
      hint: '1 / taille de la plus petite coalition majoritaire.',
    },
    gerrymander_resistance: {
      label: 'Résistance au charcutage',
      hint: 'Stabilité des sièges quand la carte des circonscriptions change (re-découpage x→y).',
    },
  },
  presets: {
    two_party: {
      label: 'Bipartisme',
      desc: 'Deux camps sur un axe gauche–droite — le terrain du votant médian.',
    },
    fragmented: {
      label: 'Multipartisme fragmenté',
      desc: 'Six partis en 2D — proportionnelle, seuils et coalitions.',
    },
    single_issue: {
      label: 'Enjeu unique',
      desc: 'Trois options sur un seul axe — la clarté du votant médian.',
    },
    france2002_like: {
      label: 'France 2002 (synthétique)',
      desc: 'Gauche fragmentée, extrêmes polarisés — le terrain du spoiler.',
    },
    usa2000_like: {
      label: 'USA 2000 (synthétique)',
      desc: 'Nader spoile Gore — Bush gagne en pluralité malgré Gore vainqueur de Condorcet.',
    },
    weimar1932_like: {
      label: 'Weimar 1932 (synthétique)',
      desc: 'Cinq partis polarisés, PR sans seuil — aucune majorité sans les extrêmes.',
    },
  },
  manip: {
    plurality: { label: 'P (calcul trivial)', ref: 'compromission directe' },
    approval: { label: 'P (calcul trivial)', ref: 'approuver le challenger' },
    score: { label: 'P (calcul trivial)', ref: 'note maximale au challenger' },
    star: { label: 'P (note + finale)', ref: 'STAR — note puis duel' },
    majority_judgment: { label: 'P (médiane)', ref: 'Balinski–Laraki 2010' },
    borda: {
      label: 'P pour un manipulateur · NP-difficile en coalition',
      ref: 'Bartholdi–Tovey–Trick 1989 ; Betzler et al. / Davies et al. 2011',
    },
    two_round: { label: 'P (un manipulateur)', ref: 'Conitzer–Sandholm–Lang 2007' },
    condorcet: { label: 'P (Copeland)', ref: 'Bartholdi–Tovey–Trick 1989' },
    minimax: { label: 'P (paires)', ref: 'minimax — calcul polynomial' },
    schulze: { label: 'P (chemin le plus fort)', ref: 'Schulze 2011' },
    bucklin: { label: 'P (calcul direct)', ref: 'Xia et al. 2009' },
    coombs: { label: 'P (élimination par derniers)', ref: 'élimination, cf. IRV' },
    nanson: { label: 'NP-difficile à manipuler', ref: 'Narodytska–Walsh–Xia 2011' },
    baldwin: { label: 'NP-difficile à manipuler', ref: 'Narodytska–Walsh–Xia 2011' },
    irv: {
      label: 'NP-difficile, même pour un seul manipulateur',
      ref: 'Bartholdi–Orlin 1991 (STV/IRV)',
    },
    ranked_pairs: { label: 'P (paires ordonnées)', ref: 'Tideman 1987 — calcul polynomial' },
    random_ballot: {
      label: 'Inmanipulable — la stratégie n’apporte rien',
      ref: 'Gibbard 1977 (seule règle non-manipulable, au prix du hasard)',
    },
    anti_plurality: { label: 'P (véto)', ref: 'règle positionnelle' },
    dowdall: { label: 'P (positionnel)', ref: 'règle positionnelle' },
    black: { label: 'P (Condorcet/Borda)', ref: 'Black 1958' },
    smith_irv: { label: 'NP-difficile (composante IRV)', ref: 'Tideman 1987' },
    split_cycle: { label: 'P (chemins)', ref: 'Holliday–Pacuit 2021' },
    kemeny: { label: 'NP-difficile', ref: 'Bartholdi–Tovey–Trick 1989' },
    cumulative: { label: 'P (répartition)', ref: 'règle cardinale' },
    maximin: { label: 'P (min d’utilité)', ref: 'règle cardinale' },
    benham: { label: 'NP-difficile (composante IRV)', ref: 'Condorcet-IRV' },
    river: { label: 'P (chemins)', ref: 'Heitzig 2004' },
    nash: { label: 'P (produit)', ref: 'règle cardinale' },
    raynaud: { label: 'P (paires)', ref: 'élimination par pire défaite' },
  },

  gallery: {
    eyebrow: 'À DÉCOUVRIR',
    title: 'Galerie des méthodes',
    intro:
      'Toutes les méthodes de vote sur une même page — les plus courantes d’abord, puis les plus spécifiques. Chacune avec une analogie de la vie courante, le vainqueur sur votre électorat actuel, et une animation pas à pas de son dépouillement.',
    watch: '▶ Voir le déroulé',
    liveWinner: 'Vainqueur avec votre électorat actuel',
  },
  duel: {
    eyebrow: 'FACE-À-FACE',
    title: 'Comparer deux méthodes',
    intro:
      'Deux méthodes, les mêmes bulletins, dépouillés côte à côte. Choisissez une règle de chaque côté et regardez le décompte : le vainqueur dépend-il de la méthode ?',
    winner: 'Vainqueur',
    verdictSame: 'Même vainqueur des deux côtés : {{name}}. Ici, la méthode ne change rien.',
    verdictDiffer:
      'Vainqueurs différents : {{a}} à gauche, {{b}} à droite. La méthode change le résultat.',
    replayBoth: 'Rejouer les deux',
    needCandidates: 'Ajoutez au moins deux candidats dans le Playground.',
  },
  lab: {
    eyebrow: 'VOTE LAB · ANALYSES AVANCÉES',
    title: 'Laboratoire',
    intro:
      "Outils d'exploration approfondie — paradoxes, théorie du choix social, mécanismes alternatifs, dynamiques temporelles. Configurez d'abord une élection dans le Playground, puis explorez ici.",
    backToPlayground: 'Retour au Playground',
    instrumentHint:
      'Cette carte reste la même pour toutes les sections ci-contre — changez la règle, l’électorat ou la lentille ici, les analyses se mettent à jour.',
    mechanisms: {
      title: '⚙️ Procédures de décision alternatives',
      subtitle: 'jury, NOTA, démocratie liquide, sortition…',
    },
    systems: {
      title: '🏛 Systèmes électoraux & circonscriptions',
      subtitle: 'coalitions, STV, charcutage, pipeline…',
    },
    campaign: {
      title: '🎬 Trajectoires de campagne',
      subtitle: 'Hotelling, sondages, polarisation, dynamique des partis',
    },
    temporal: {
      title: '🔁 Mécanismes temporels',
      subtitle: 'vote adaptatif, replay historique, primaires, cascade, fatigue',
    },
    behavioral: {
      title: '🧠 Réalisme comportemental',
      subtitle: 'biais, électeur timide, surcharge, vote obligatoire, polarisation affective',
    },
    analysis: {
      title: '🔬 Analyse approfondie',
      subtitle: 'Monte-Carlo, manipulabilité, volonté collective, effets combinés',
    },
    theory: {
      title: '📚 Théorie & paradoxes du choix social',
      subtitle: 'Sen, jugement, agenda, tyrannie, apportionnement, Pol.is',
    },
    blank: {
      title: '⬜ Vote blanc & abstention',
      subtitle: 'ne pas choisir, refuser l’offre — et ce que la règle en fait',
    },
    results: {
      title: '📋 Résultats complets',
      subtitle: 'dépouillement détaillé, animation du comptage',
    },
    ballot: {
      title: '🗳️ Bulletin de vote (expression)',
      subtitle: 'type de bulletin, expressivité, charge cognitive',
    },
    strategy: {
      title: '🎯 Analyse stratégique approfondie',
      subtitle: 'sincérité, vulnérabilité Gibbard–Satterthwaite, équilibre itéré',
    },
    values: {
      title: '⚖️ Valeurs & sensibilité',
      subtitle: 'cadran Lijphart, frontière de Pareto',
    },
    groups: {
      methods: 'Méthodes',
      rules: 'Règles & stratégie',
      systems: 'Systèmes & mécanismes',
      dynamics: 'Dynamiques',
      theory: 'Théorie & analyse',
      blank: 'Vote blanc & abstention',
    },
    compareElec: 'Comparer un électorat',
    comparePick: 'Comparer la même fiche sur :',
    compareStop: 'Fermer la comparaison',
    elecCurrent: 'Électorat actuel',
    matrix: {
      title: 'Comparaison des méthodes',
      liveRow: 'Vainqueur avec votre électorat actuel',
      familyMajoritarian: 'Majorité',
      familyOrdinal: 'Ordinal',
      familyCondorcet: 'Condorcet',
      familyCardinal: 'Cardinal',
      criteria: {
        condorcet_winner: 'Élit le gagnant Condorcet',
        condorcet_loser: 'Élimine le perdant Condorcet',
        majority: 'Critère majoritaire',
        monotonicity: 'Monotonie',
        iia: 'IIA',
        strategy_proof: 'Résistance à la stratégie',
        participation: 'Participation',
        reversal: 'Symétrie de révocation',
      },
    },
  },
};

export type PlaygroundKeys = typeof pgFr;
export default pgFr;
