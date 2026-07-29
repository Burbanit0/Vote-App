// methodInfo — pedagogical content for every voting method the playground can
// show. Consumed by <MethodInfo> (the ⓘ hover/click popover) wherever a method
// name is rendered: the Bilan title, the ValuesPanel lens, the full-results table.
//
// Why a co-located TS registry (vs i18n keys like MetricTooltip): the copy is
// long-form, domain-specific voting theory that the maintainer wants to review and
// tune in one place. Each entry is bilingual; the component picks fr/en from i18n.
//
// Keys are the CANONICAL method ids. Backend/result-table ids that differ
// (copeland, star_voting, simple_score, …) are mapped via METHOD_ALIASES so a
// single entry serves every surface.

export type MethodFamily = 'ordinal' | 'condorcet' | 'cardinal' | 'apportionment';

export interface MethodCopy {
  /** Display name (matches the playground label). */
  name: string;
  /** One-sentence plain-language gist. */
  summary: string;
  /** How the rule actually decides the winner. */
  how: string;
  /** What it does well. */
  strength: string;
  /** Its main failure mode / vulnerability. */
  weakness: string;
  /** Axiomatic stance (Condorcet, monotonicity, strategy-resistance…). */
  criterion: string;
  /** A concrete, memorable illustration. */
  example: string;
}

export interface MethodEntry {
  family: MethodFamily;
  /** True for the Condorcet family — gets the live "no Condorcet winner" note. */
  condorcet?: boolean;
  fr: MethodCopy;
  en: MethodCopy;
}

// Result-table / backend ids → canonical registry key.
export const METHOD_ALIASES: Record<string, string> = {
  copeland: 'condorcet',
  star_voting: 'star',
  simple_score: 'score',
  positional: 'score',
  kemeny: 'kemeny_young',
};

export function methodKey(id: string): string {
  return METHOD_ALIASES[id] ?? id;
}

// "Au quotidien" — one everyday analogy per method, the Phase-6 polish that
// grounds an abstract rule in a situation anyone has lived. A parallel bilingual
// map (like METHOD_ALIASES) rather than a field on every entry: bounded to the
// methods a newcomer actually meets; MethodInfo shows it only when present. Keyed
// by canonical id (via methodKey), so aliases resolve for free.
export const METHOD_ANALOGY: Record<string, { fr: string; en: string }> = {
  plurality: {
    fr: 'Comme choisir un resto à plusieurs en criant chacun un seul nom : le plus crié gagne, même si personne d’autre ne l’aime.',
    en: 'Like picking a restaurant by everyone shouting one name: the most-shouted wins, even if no one else likes it.',
  },
  two_round: {
    fr: 'Comme une demi-finale puis une finale : on garde les deux favoris, puis on tranche entre eux.',
    en: 'Like a semi-final then a final: keep the top two, then decide between them.',
  },
  irv: {
    fr: 'Comme un jeu d’élimination : à chaque tour le dernier sort, et ses supporters reportent leur voix sur qui leur reste.',
    en: 'Like a knockout game: each round the last-placed is out, and their fans move their vote to whoever’s left.',
  },
  coombs: {
    fr: 'Comme éliminer d’abord le plat que le plus de gens refusent, jusqu’à ce qu’il n’en reste qu’un.',
    en: 'Like removing the dish the most people reject first, until only one is left.',
  },
  borda: {
    fr: 'Comme un podium qui donne des points : 3 pour un 1er, 2 pour un 2e, 1 pour un 3e — le plus grand total gagne.',
    en: 'Like a podium awarding points: 3 for a 1st, 2 for a 2nd, 1 for a 3rd — the biggest total wins.',
  },
  condorcet: {
    fr: 'Comme un championnat toutes-rondes : le vainqueur est celui qui bat chaque adversaire en match direct.',
    en: 'Like a round-robin league: the winner is the one who beats every rival in a head-to-head match.',
  },
  approval: {
    fr: 'Comme cocher tous les restos qui te vont : celui que le plus de gens acceptent l’emporte.',
    en: 'Like ticking every restaurant that works for you: the one most people find acceptable wins.',
  },
  score: {
    fr: 'Comme des notes de film en étoiles : chacun note tout le monde, la meilleure moyenne gagne.',
    en: 'Like star-rating films: everyone rates everyone, the best average wins.',
  },
  star: {
    fr: 'Comme noter en étoiles, puis départager les deux mieux notés par un duel direct.',
    en: 'Like star-rating, then settling the top two with a direct head-to-head.',
  },
  cumulative: {
    fr: 'Comme un budget de jetons à répartir : tout sur un candidat, ou étalé sur plusieurs.',
    en: 'Like a budget of tokens to spread: all on one candidate, or split across several.',
  },
  kemeny_young: {
    fr: 'Comme trancher un débat en essayant tous les classements possibles et en gardant celui qui contredit le moins de monde.',
    en: 'Like settling an argument by trying every possible ranking and keeping the one that contradicts the fewest people.',
  },
};

/** Everyday analogy for a method in one language, or null if none. */
export function methodAnalogy(id: string, lang: Lang): string | null {
  return METHOD_ANALOGY[methodKey(id)]?.[lang] ?? null;
}

export const METHOD_INFO: Record<string, MethodEntry> = {
  plurality: {
    family: 'ordinal',
    fr: {
      name: 'Pluralité (1 tour)',
      summary: 'Chacun vote pour un seul candidat ; celui qui a le plus de voix gagne.',
      how: 'On ne compte que la première préférence de chaque électeur ; la majorité relative suffit.',
      strength: 'Extrêmement simple à comprendre, à voter et à dépouiller.',
      weakness:
        'Vote utile massif et effet « spoiler » : un troisième candidat proche divise un camp et le fait perdre.',
      criterion: 'Échoue au critère de Condorcet ; très sensible au découpage de l’offre.',
      example: 'Un candidat peut l’emporter avec 30 % si ses adversaires se divisent le reste.',
    },
    en: {
      name: 'Plurality (first-past-the-post)',
      summary: 'Each voter picks one candidate; whoever gets the most votes wins.',
      how: 'Only each voter’s first preference is counted; a relative majority is enough.',
      strength: 'Dead simple to understand, to vote, and to count.',
      weakness:
        'Heavy strategic voting and the spoiler effect: a similar third candidate splits a camp and hands it the loss.',
      criterion: 'Fails the Condorcet criterion; very sensitive to how the field is split.',
      example: 'A candidate can win on 30 % if opponents split the rest.',
    },
  },
  two_round: {
    family: 'ordinal',
    fr: {
      name: 'Deux tours',
      summary: 'Si personne ne dépasse 50 %, les deux premiers s’affrontent dans un second tour.',
      how: '1er tour aux premières voix ; le 2e tour est un duel entre les deux meilleurs.',
      strength: 'Donne au vainqueur une légitimité majoritaire et réduit un peu le vote utile.',
      weakness:
        'Peut éliminer dès le 1er tour un candidat qui battrait tout le monde en duel (vainqueur de Condorcet) ; non monotone.',
      criterion: 'Échoue Condorcet et la monotonie (mieux voté peut faire perdre).',
      example: 'France 2002 : un centriste battu au 1er tour aurait pu gagner tous les duels.',
    },
    en: {
      name: 'Two-round runoff',
      summary: 'If nobody passes 50 %, the top two meet in a second round.',
      how: 'Round 1 on first preferences; round 2 is a duel between the top two.',
      strength: 'Gives the winner majority legitimacy and softens strategic voting a little.',
      weakness:
        'Can eliminate in round 1 a candidate who would beat everyone head-to-head (the Condorcet winner); non-monotonic.',
      criterion: 'Fails Condorcet and monotonicity (more support can backfire).',
      example: 'France 2002: a centrist knocked out in round 1 would have won every duel.',
    },
  },
  irv: {
    family: 'ordinal',
    fr: {
      name: 'Vote alternatif (IRV)',
      summary: 'Classement complet ; on élimine le dernier et on transfère ses voix, jusqu’à 50 %.',
      how: 'À chaque tour, le candidat avec le moins de premières voix est éliminé et ses bulletins reportés au suivant.',
      strength:
        'Réduit fortement le vote utile : on peut classer son favori en premier sans risque direct.',
      weakness: 'Non monotone et sensible à l’ordre d’élimination ; peut écarter un Condorcet.',
      criterion: 'Échoue Condorcet et monotonie ; résiste mieux au spoiler que la pluralité.',
      example: 'Australie (Chambre des représentants) utilise l’IRV depuis 1918.',
    },
    en: {
      name: 'Instant-runoff (IRV / AV)',
      summary: 'Full ranking; eliminate the last and transfer its votes until someone hits 50 %.',
      how: 'Each round drops the candidate with the fewest first votes and reassigns those ballots.',
      strength:
        'Strongly reduces strategic voting: you can rank your favourite first without direct risk.',
      weakness: 'Non-monotonic and sensitive to elimination order; can drop a Condorcet winner.',
      criterion: 'Fails Condorcet and monotonicity; far more spoiler-resistant than plurality.',
      example: 'Australia’s House of Representatives has used IRV since 1918.',
    },
  },
  borda: {
    family: 'ordinal',
    fr: {
      name: 'Borda',
      summary: 'Chaque rang donne des points (n−1, n−2, …) ; le plus de points gagne.',
      how: 'On somme les points de rang sur tous les bulletins.',
      strength: 'Favorise les candidats de consensus, larges et peu clivants.',
      weakness: 'Très manipulable par enterrement (« burying ») et sensible aux candidats clones.',
      criterion:
        'Échoue Condorcet ; tient compte de toute la préférence, pas seulement du premier choix.',
      example: 'Utilisé pour des prix sportifs et le parlement de Nauru (variante Dowdall).',
    },
    en: {
      name: 'Borda count',
      summary: 'Each rank scores points (n−1, n−2, …); most points wins.',
      how: 'Sum the positional points across all ballots.',
      strength: 'Rewards broad, consensual, low-polarisation candidates.',
      weakness: 'Highly manipulable by burying, and sensitive to clone candidates.',
      criterion: 'Fails Condorcet; uses the whole ranking, not just the top choice.',
      example: 'Used for sports awards and Nauru’s parliament (Dowdall variant).',
    },
  },
  approval: {
    family: 'cardinal',
    fr: {
      name: 'Approbation',
      summary: 'On approuve autant de candidats qu’on veut ; le plus approuvé gagne.',
      how: 'Chaque approbation vaut 1 point ; on additionne.',
      strength:
        'Très simple, supprime le dilemme « diviser ou voter utile », tolère beaucoup de candidats.',
      weakness: 'Le seuil d’approbation est stratégique : où placer la barre reste un calcul.',
      criterion: 'Ne respecte pas toujours Condorcet ; un seul bulletin, énormément d’information.',
      example: 'Utilisé par plusieurs sociétés savantes (IEEE, MAA) pour leurs élections internes.',
    },
    en: {
      name: 'Approval voting',
      summary: 'Approve as many candidates as you like; the most-approved wins.',
      how: 'Each approval is worth one point; sum them.',
      strength: 'Very simple, removes the split-vs-strategic dilemma, scales to many candidates.',
      weakness:
        'The approval threshold is itself strategic — where to draw the line is a calculation.',
      criterion: 'Not always Condorcet-consistent; one ballot, a lot of information.',
      example: 'Used by several learned societies (IEEE, MAA) for internal elections.',
    },
  },
  condorcet: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Condorcet (Copeland)',
      summary:
        'Élit qui gagnerait en duel contre chaque autre ; Copeland départage par bilan des duels.',
      how: 'On simule tous les face-à-face ; Copeland classe par (victoires − défaites) de duel.',
      strength: 'Respecte par construction le vainqueur de Condorcet quand il existe.',
      weakness: 'Quand les préférences tournent en rond (cycle), il n’existe pas de tel vainqueur.',
      criterion: 'Respecte Condorcet ; départage les cycles par décompte de duels.',
      example: 'A bat B, B bat C, C bat A : aucun vainqueur de Condorcet — c’est le paradoxe.',
    },
    en: {
      name: 'Condorcet (Copeland)',
      summary: 'Elects whoever would win every head-to-head; Copeland breaks ties by duel record.',
      how: 'Simulate all pairwise duels; Copeland ranks by (duel wins − losses).',
      strength: 'By construction elects the Condorcet winner whenever one exists.',
      weakness: 'When preferences cycle, no such winner exists.',
      criterion: 'Satisfies Condorcet; resolves cycles by duel count.',
      example: 'A beats B, B beats C, C beats A: no Condorcet winner — the paradox.',
    },
  },
  minimax: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Condorcet (minimax)',
      summary:
        'Méthode de Condorcet qui élit le candidat dont la pire défaite en duel est la moins grave.',
      how: 'Pour chaque candidat on retient sa plus forte défaite ; on choisit celui dont ce maximum est minimal.',
      strength: 'Respecte Condorcet et reste simple à expliquer même en présence de cycles.',
      weakness: 'Peut violer le critère de Smith (élire hors de l’ensemble dominant).',
      criterion: 'Respecte Condorcet ; règle de cycle « pessimiste » (on minimise le pire).',
      example: 'En cas de cycle serré, choisit celui qui « perd le moins fort ».',
    },
    en: {
      name: 'Condorcet (minimax)',
      summary:
        'A Condorcet method electing the candidate whose worst pairwise defeat is least bad.',
      how: 'For each candidate take their largest defeat; pick the one whose worst loss is smallest.',
      strength: 'Satisfies Condorcet and stays easy to explain even under cycles.',
      weakness: 'Can violate the Smith criterion (elect outside the dominating set).',
      criterion: 'Satisfies Condorcet; a “pessimistic” cycle rule (minimise the worst loss).',
      example: 'In a tight cycle, picks whoever “loses least badly”.',
    },
  },
  schulze: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Condorcet (Schulze)',
      summary: 'Méthode de Condorcet par « chemins les plus forts » entre candidats.',
      how: 'On cherche, pour chaque paire, le chemin de duels le plus fort (force = plus petite marge du chemin).',
      strength: 'Respecte Condorcet et le critère de Smith ; bonne résistance aux clones.',
      weakness: 'Plus difficile à expliquer au grand public (algorithme de type Floyd-Warshall).',
      criterion: 'Respecte Condorcet, Smith, monotonie et clones — l’une des plus robustes.',
      example: 'Utilisée par Debian, Wikimedia, le Parti Pirate pour leurs votes internes.',
    },
    en: {
      name: 'Condorcet (Schulze)',
      summary: 'A Condorcet method based on the “strongest paths” between candidates.',
      how: 'For each pair, find the strongest chain of duels (a path’s strength is its weakest link).',
      strength: 'Satisfies Condorcet and the Smith criterion; strong clone resistance.',
      weakness: 'Harder to explain to the public (a Floyd-Warshall-style algorithm).',
      criterion: 'Satisfies Condorcet, Smith, monotonicity and clones — among the most robust.',
      example: 'Used by Debian, Wikimedia and the Pirate Party for internal votes.',
    },
  },
  bucklin: {
    family: 'ordinal',
    fr: {
      name: 'Bucklin',
      summary:
        'On élargit le décompte aux 1ers, puis 2es, … rangs jusqu’à ce qu’un candidat passe la majorité.',
      how: 'On ajoute rang par rang les voix de chacun ; le premier à dépasser 50 % gagne.',
      strength: 'Trouve vite un candidat largement acceptable.',
      weakness: 'Manipulable : tronquer son classement peut aider son favori.',
      criterion: 'Échoue Condorcet ; logique de « majorité médiane » par paliers.',
      example: 'Utilisé dans plusieurs villes américaines au début du XXe siècle.',
    },
    en: {
      name: 'Bucklin',
      summary: 'Widen the count to 1st, then 2nd, … ranks until someone clears a majority.',
      how: 'Add each candidate’s votes rank by rank; the first past 50 % wins.',
      strength: 'Quickly finds a broadly acceptable candidate.',
      weakness: 'Manipulable: truncating your ranking can help your favourite.',
      criterion: 'Fails Condorcet; a tiered “median majority” logic.',
      example: 'Used by several US cities in the early 20th century.',
    },
  },
  coombs: {
    family: 'ordinal',
    fr: {
      name: 'Coombs',
      summary: 'Comme l’IRV, mais on élimine le candidat le plus souvent classé DERNIER.',
      how: 'À chaque tour on retire le plus rejeté (dernières places) jusqu’à une majorité.',
      strength: 'Pénalise les candidats clivants ; favorise l’acceptabilité large.',
      weakness: 'Non monotone et sensible à la troncature des bulletins.',
      criterion: 'Échoue Condorcet ; miroir « par le bas » de l’IRV.',
      example: 'Plus théorique que pratique, utile pour contraster avec l’IRV.',
    },
    en: {
      name: 'Coombs',
      summary: 'Like IRV, but eliminate the candidate most often ranked LAST.',
      how: 'Each round removes the most-rejected (last-place) candidate until a majority.',
      strength: 'Punishes polarising candidates; rewards broad acceptability.',
      weakness: 'Non-monotonic and sensitive to ballot truncation.',
      criterion: 'Fails Condorcet; a “bottom-up” mirror of IRV.',
      example: 'More theoretical than practical, useful to contrast with IRV.',
    },
  },
  nanson: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Nanson',
      summary:
        'Borda itératif : on élimine les candidats sous la moyenne de Borda, et on recommence.',
      how: 'À chaque tour, retire ceux dont le score de Borda est sous la moyenne des restants.',
      strength: 'Respecte Condorcet tout en gardant l’esprit consensuel de Borda.',
      weakness: 'Non monotone ; plusieurs tours de recalcul.',
      criterion: 'Respecte Condorcet (élit le vainqueur de Condorcet quand il existe).',
      example: 'Proposé par E. J. Nanson en 1882 pour corriger Borda.',
    },
    en: {
      name: 'Nanson',
      summary: 'Iterated Borda: eliminate candidates below the average Borda score, then repeat.',
      how: 'Each round drops those whose Borda score is below the remaining average.',
      strength: 'Satisfies Condorcet while keeping Borda’s consensual spirit.',
      weakness: 'Non-monotonic; multiple recomputation rounds.',
      criterion: 'Satisfies Condorcet (elects the Condorcet winner when one exists).',
      example: 'Proposed by E. J. Nanson in 1882 to fix Borda.',
    },
  },
  baldwin: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Baldwin',
      summary: 'Comme Nanson, mais on élimine UN seul candidat (le plus faible Borda) par tour.',
      how: 'À chaque tour, retire le candidat au plus bas score de Borda parmi les restants.',
      strength: 'Respecte Condorcet ; élimination plus douce que Nanson.',
      weakness: 'Non monotone ; coûteux (recalcul de Borda à chaque tour).',
      criterion: 'Respecte Condorcet.',
      example: 'Variante de Nanson attribuée à Joseph Baldwin.',
    },
    en: {
      name: 'Baldwin',
      summary: 'Like Nanson, but eliminate ONE candidate (lowest Borda) per round.',
      how: 'Each round drops the single lowest-Borda candidate among those remaining.',
      strength: 'Satisfies Condorcet; gentler elimination than Nanson.',
      weakness: 'Non-monotonic; costly (Borda recomputed each round).',
      criterion: 'Satisfies Condorcet.',
      example: 'A Nanson variant attributed to Joseph Baldwin.',
    },
  },
  ranked_pairs: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Condorcet — paires ordonnées (Tideman)',
      summary:
        'On verrouille les duels les plus nets d’abord, en sautant ceux qui créeraient un cycle.',
      how: 'Trie tous les duels par marge décroissante ; ajoute chaque duel au classement sauf s’il boucle un cycle. Le sommet du graphe obtenu gagne.',
      strength:
        'Respecte Condorcet ET l’indépendance aux clones ; la plus « explicable » des méthodes de Condorcet.',
      weakness:
        'Bulletin classé complet ; départage des marges égales à préciser ; reste manipulable.',
      criterion: 'Respecte Condorcet, la monotonie et l’indépendance aux clones (Tideman 1987).',
      example:
        'Utilisée par plusieurs organisations open-source pour départager des cycles de duels.',
    },
    en: {
      name: 'Ranked Pairs (Tideman)',
      summary: 'Lock the most decisive head-to-heads first, skipping any that would form a cycle.',
      how: 'Sort every duel by margin (largest first); add each to the order unless it closes a cycle. The source of the resulting graph wins.',
      strength:
        'Satisfies Condorcet AND clone-independence; the most "explainable" Condorcet method.',
      weakness:
        'Needs full rankings; equal-margin tie-breaks must be specified; still manipulable.',
      criterion: 'Satisfies Condorcet, monotonicity and clone-independence (Tideman 1987).',
      example: 'Used by several open-source organisations to resolve cycles of pairwise duels.',
    },
  },
  random_ballot: {
    family: 'ordinal',
    fr: {
      name: 'Vote au sort (loterie / dictateur aléatoire)',
      summary:
        'On tire un bulletin au hasard ; son premier choix l’emporte. La probabilité de gagner = la part de premières voix.',
      how: 'Chaque électeur indique un favori ; un bulletin est tiré uniformément au sort et son premier choix est élu.',
      strength:
        'Seule règle vraiment non-manipulable (Gibbard 1977) : mentir n’améliore jamais son espérance. Représentation proportionnelle en probabilité.',
      weakness:
        'Le hasard peut élire un candidat minoritaire ; résultat non reproductible et politiquement contre-intuitif.',
      criterion:
        'Non-manipulable et neutre/anonyme — au prix du déterminisme (théorème de Gibbard 1977).',
      example:
        'Référence théorique : la « lentille Probabilité » montre la loterie ; ici le vainqueur affiché est l’issue la plus probable.',
    },
    en: {
      name: 'Random ballot (lottery / random dictator)',
      summary:
        'Draw one ballot at random; its first choice wins. Win probability = first-preference share.',
      how: 'Each voter names a favourite; a single ballot is drawn uniformly at random and its top choice is elected.',
      strength:
        'The only genuinely strategyproof rule (Gibbard 1977): lying never improves your expectation. Proportional in probability.',
      weakness:
        'Randomness can elect a minority candidate; the outcome is non-reproducible and politically counter-intuitive.',
      criterion: 'Strategyproof and neutral/anonymous — at the cost of determinism (Gibbard 1977).',
      example:
        'A theoretical benchmark: the "Probability lens" shows the lottery; the displayed winner is the most likely outcome.',
    },
  },
  star: {
    family: 'cardinal',
    fr: {
      name: 'STAR (note puis duel)',
      summary:
        'On note chaque candidat (0–5), puis duel automatique entre les deux meilleures moyennes.',
      how: 'Phase 1 : moyennes des notes. Phase 2 : sur les deux premiers, on compte qui est mieux noté bulletin par bulletin.',
      strength: 'Combine l’expressivité des notes et la légitimité d’un duel final.',
      weakness: 'Un peu plus complexe à expliquer ; les notes restent stratégiques.',
      criterion: 'Bonne résistance stratégique ; le runoff corrige l’exagération des notes.',
      example: 'Promu par l’Equal Vote Coalition (Oregon) comme alternative à l’IRV.',
    },
    en: {
      name: 'STAR (Score Then Automatic Runoff)',
      summary:
        'Score each candidate (0–5), then an automatic runoff between the two highest averages.',
      how: 'Phase 1: average scores. Phase 2: among the top two, count who each ballot rates higher.',
      strength: 'Combines the expressiveness of scores with the legitimacy of a final duel.',
      weakness: 'Slightly harder to explain; scores remain strategic.',
      criterion: 'Good strategy resistance; the runoff corrects score exaggeration.',
      example: 'Promoted by the Equal Vote Coalition (Oregon) as an IRV alternative.',
    },
  },
  majority_judgment: {
    family: 'cardinal',
    fr: {
      name: 'Jugement majoritaire',
      summary:
        'On attribue une mention (Excellent…À rejeter) ; gagne la meilleure mention médiane.',
      how: 'Chaque candidat reçoit la mention médiane de ses bulletins ; on départage finement les médianes égales.',
      strength: 'Très résistant à la manipulation ; expressif et lisible (mentions).',
      weakness: 'Peut heurter l’intuition majoritaire ; sensible au libellé des mentions.',
      criterion: 'Critère de la médiane (Balinski-Laraki) plutôt que de la moyenne.',
      example: 'Proposé par Balinski & Laraki (2007), testé sur la présidentielle française.',
    },
    en: {
      name: 'Majority judgment',
      summary: 'Voters grade each candidate (Excellent…Reject); the best median grade wins.',
      how: 'Each candidate takes the median grade of their ballots; tied medians are broken finely.',
      strength: 'Very manipulation-resistant; expressive and readable (grades).',
      weakness: 'Can clash with majority intuition; sensitive to grade wording.',
      criterion: 'A median criterion (Balinski-Laraki) rather than a mean.',
      example: 'Proposed by Balinski & Laraki (2007), trialled on the French presidential race.',
    },
  },
  score: {
    family: 'cardinal',
    fr: {
      name: 'Vote par note (score)',
      summary: 'On note chaque candidat sur une échelle ; la meilleure moyenne gagne.',
      how: 'On fait la moyenne (ou la somme) des notes attribuées à chaque candidat.',
      strength: 'Le plus expressif : on dit non seulement qui on préfère, mais à quel point.',
      weakness: 'Incite à l’exagération (mettre 0 ou max) — la sincérité n’est pas optimale.',
      criterion: 'Maximise une utilité déclarée ; ne respecte pas toujours Condorcet.',
      example: 'Cœur des systèmes de notation en ligne ; base de STAR et du regret bayésien.',
    },
    en: {
      name: 'Score (range) voting',
      summary: 'Rate each candidate on a scale; the highest average wins.',
      how: 'Average (or sum) the scores each candidate receives.',
      strength: 'The most expressive: you say not just who you prefer but by how much.',
      weakness: 'Encourages exaggeration (give 0 or max) — sincerity isn’t optimal.',
      criterion: 'Maximises a declared utility; not always Condorcet-consistent.',
      example: 'The core of online rating systems; the basis of STAR and Bayesian regret.',
    },
  },
  kemeny_young: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Kemeny-Young',
      summary: 'Cherche le classement global le plus « d’accord » avec tous les bulletins.',
      how: 'On choisit l’ordre qui minimise le total des désaccords par paires (distance de Kendall).',
      strength: 'Respecte Condorcet et donne un classement complet, pas seulement un gagnant.',
      weakness: 'Coût combinatoire (O(n!)) : exact seulement jusqu’à ~6 candidats, sinon approché.',
      criterion: 'Respecte Condorcet et la réversibilité ; optimum de « consensus médian ».',
      example:
        'Au-delà de 8 candidats, le playground bascule sur Borda (une approximation) plutôt que la recherche exhaustive.',
    },
    en: {
      name: 'Kemeny-Young',
      summary: 'Finds the overall ranking that best agrees with every ballot.',
      how: 'Pick the order minimising total pairwise disagreement (Kendall-tau distance).',
      strength: 'Satisfies Condorcet and yields a full ranking, not just a winner.',
      weakness: 'Combinatorial cost (O(n!)): exact only up to ~6 candidates, else approximated.',
      criterion: 'Satisfies Condorcet and reversal symmetry; a “median consensus” optimum.',
      example:
        'Beyond 8 candidates, the playground falls back to Borda (an approximation) instead of the exhaustive search.',
    },
  },
  median_voting: {
    family: 'cardinal',
    fr: {
      name: 'Vote médian',
      summary:
        'Comme le score, mais on retient la note MÉDIANE de chaque candidat, pas la moyenne.',
      how: 'On classe les candidats par leur note médiane sur tous les bulletins.',
      strength: 'Robuste aux notes extrêmes : un seul 0 ou 5 ne fait pas basculer.',
      weakness: 'Perd de l’information de marge ; nombreux ex æquo de médiane.',
      criterion: 'Esprit médian (cousin du jugement majoritaire, sans le départage fin).',
      example: 'Sert de comparateur « moyenne vs médiane » dans la table des résultats.',
    },
    en: {
      name: 'Median voting',
      summary: 'Like score voting, but keep each candidate’s MEDIAN score, not the mean.',
      how: 'Rank candidates by the median of their scores across all ballots.',
      strength: 'Robust to extreme scores: a lone 0 or 5 won’t swing it.',
      weakness: 'Loses margin information; many median ties.',
      criterion: 'A median spirit (cousin of majority judgment, without the fine tie-break).',
      example: 'Acts as a “mean vs median” comparator in the results table.',
    },
  },
  mean_median_hybrid: {
    family: 'cardinal',
    fr: {
      name: 'Hybride moyenne-médiane',
      summary: 'Compromis : moitié moyenne des notes, moitié médiane.',
      how: 'Score final = 0,5 × moyenne + 0,5 × médiane de chaque candidat.',
      strength: 'Garde la finesse de la moyenne tout en amortissant les notes extrêmes.',
      weakness: 'Pondération 50/50 arbitraire ; pas de fondement axiomatique fort.',
      criterion: 'Heuristique pratique, entre score et vote médian.',
      example: 'Illustre qu’on peut « régler le curseur » entre moyenne et médiane.',
    },
    en: {
      name: 'Mean-median hybrid',
      summary: 'A compromise: half the mean of scores, half the median.',
      how: 'Final score = 0.5 × mean + 0.5 × median for each candidate.',
      strength: 'Keeps the mean’s precision while damping extreme scores.',
      weakness: 'The 50/50 weighting is arbitrary; no strong axiomatic basis.',
      criterion: 'A practical heuristic, between score and median voting.',
      example: 'Shows you can “dial” between mean and median.',
    },
  },
  variance_based: {
    family: 'cardinal',
    fr: {
      name: 'Score pondéré par la variance',
      summary: 'Récompense les candidats bien notés ET consensuels (faible dispersion).',
      how: 'Score = moyenne − 0,5 × écart-type des notes : on pénalise la division.',
      strength: 'Met en avant les candidats rassembleurs plutôt que clivants.',
      weakness: 'La pénalité de variance est un choix arbitraire ; manipulable.',
      criterion: 'Heuristique « consensus » ; pas de garantie axiomatique.',
      example: 'Un candidat noté 3 partout peut battre un 5/0 très clivant.',
    },
    en: {
      name: 'Variance-penalised score',
      summary: 'Rewards candidates who are well-rated AND consensual (low spread).',
      how: 'Score = mean − 0.5 × standard deviation of ratings: division is penalised.',
      strength: 'Surfaces unifying candidates over polarising ones.',
      weakness: 'The variance penalty is an arbitrary choice; manipulable.',
      criterion: 'A “consensus” heuristic; no axiomatic guarantee.',
      example: 'A flat-3 candidate can beat a polarising 5/0 one.',
    },
  },

  // ── Parliament structures (seat allocation) ────────────────────────────────
  pr: {
    family: 'apportionment',
    fr: {
      name: 'Proportionnelle (listes)',
      summary: 'Les sièges sont répartis en proportion des voix de chaque parti.',
      how: 'Une règle d’apportionnement (D’Hondt, Sainte-Laguë) convertit les % de voix en sièges, souvent au-dessus d’un seuil.',
      strength: 'Représentation fidèle : peu de voix gaspillées, pluralisme préservé.',
      weakness: 'Fragmentation possible : majorités de coalition, parfois instables.',
      criterion: 'Vise la proportionnalité (faible indice de Gallagher).',
      example: 'Pays-Bas, Israël : assemblées très proportionnelles et multipartites.',
    },
    en: {
      name: 'Proportional (party lists)',
      summary: 'Seats are shared in proportion to each party’s vote share.',
      how: 'An apportionment rule (D’Hondt, Sainte-Laguë) turns vote % into seats, usually above a threshold.',
      strength: 'Faithful representation: few wasted votes, pluralism preserved.',
      weakness: 'Possible fragmentation: coalition majorities, sometimes unstable.',
      criterion: 'Targets proportionality (low Gallagher index).',
      example: 'Netherlands, Israel: highly proportional, multi-party assemblies.',
    },
  },
  fptp: {
    family: 'apportionment',
    fr: {
      name: 'Circonscriptions (FPTP)',
      summary: 'Une circonscription = un siège, gagné par le candidat en tête localement.',
      how: 'Le territoire est découpé en bandes d’égale population ; pluralité dans chacune.',
      strength: 'Lien élu–territoire fort ; tend à dégager des majorités nettes.',
      weakness: 'Forte distorsion voix/sièges et sensibilité au découpage (charcutage).',
      criterion: 'Échoue la proportionnalité ; favorise le bipartisme (loi de Duverger).',
      example:
        'Royaume-Uni, USA (Chambre) : un parti peut avoir une majorité de sièges sans majorité de voix.',
    },
    en: {
      name: 'Districts (first-past-the-post)',
      summary: 'One district = one seat, won by the locally leading candidate.',
      how: 'The territory is cut into equal-population bands; plurality wins each.',
      strength: 'Strong representative–district link; tends to manufacture clear majorities.',
      weakness: 'Large vote/seat distortion and sensitivity to the map (gerrymandering).',
      criterion: 'Fails proportionality; favours two-party systems (Duverger’s law).',
      example: 'UK, US House: a party can hold a seat majority without a vote majority.',
    },
  },
  mmp: {
    family: 'apportionment',
    fr: {
      name: 'Mixte (MMP)',
      summary: 'Moitié circonscriptions, moitié compensation proportionnelle.',
      how: 'On élit des députés locaux (FPTP) puis on ajoute des sièges de liste pour rétablir la proportionnalité globale.',
      strength: 'Combine ancrage local et proportionnalité d’ensemble.',
      weakness: 'Sièges de surplomb (« overhang ») et complexité de compréhension.',
      criterion: 'Quasi-proportionnel tout en gardant un lien territorial.',
      example: 'Allemagne, Nouvelle-Zélande : le modèle mixte de référence.',
    },
    en: {
      name: 'Mixed-member proportional (MMP)',
      summary: 'Half local districts, half proportional top-up.',
      how: 'Elect local MPs (FPTP), then add list seats to restore overall proportionality.',
      strength: 'Combines local anchoring with overall proportionality.',
      weakness: 'Overhang seats and harder-to-grasp mechanics.',
      criterion: 'Near-proportional while keeping a territorial link.',
      example: 'Germany, New Zealand: the reference mixed model.',
    },
  },

  // ── Tier B extras (gallery + replay only) ──────────────────────────────────
  anti_plurality: {
    family: 'ordinal',
    fr: {
      name: 'Anti-pluralité (véto)',
      summary: 'Chacun vote CONTRE un candidat ; celui rejeté le moins souvent gagne.',
      how: 'On compte les dernières places : le candidat le moins souvent classé dernier l’emporte.',
      strength: 'Élit un « plus petit dénominateur commun » — le candidat que personne ne déteste.',
      weakness:
        'Ignore les premières préférences : un candidat fade sans ennemi peut battre un favori clivant.',
      criterion:
        'Échoue au critère de majorité et à Condorcet ; règle positionnelle, donc monotone.',
      example:
        'Le compromis mou l’emporte sur le champion d’un camp, faute d’adversaires acharnés.',
    },
    en: {
      name: 'Anti-plurality (veto)',
      summary: 'Everyone votes AGAINST one candidate; the least-rejected wins.',
      how: 'Count last-place votes: the candidate ranked last the fewest times wins.',
      strength: 'Elects a lowest-common-denominator — the candidate nobody hates.',
      weakness:
        'Ignores first preferences: a bland candidate with no enemies can beat a divisive favourite.',
      criterion: 'Fails majority and Condorcet; a positional rule, so monotone.',
      example: 'The mild compromise beats a camp’s champion for lack of committed opponents.',
    },
  },
  dowdall: {
    family: 'ordinal',
    fr: {
      name: 'Dowdall (Nauru)',
      summary: 'Comme Borda, mais les rangs valent 1, ½, ⅓… — le 1ᵉʳ choix pèse bien plus.',
      how: 'Chaque électeur classe tout le monde ; le rang k rapporte 1/(k+1) point. On somme.',
      strength: 'Récompense fortement les premières places sans ignorer le reste du classement.',
      weakness: 'Poids arbitraires (harmoniques) ; brise la symétrie de révocation de Borda.',
      criterion: 'Positionnel comme Borda mais non linéaire ; échoue à Condorcet.',
      example: 'Utilisé à Nauru : un 1ᵉʳ choix vaut deux 2ᵉˢ choix, trois 3ᵉˢ…',
    },
    en: {
      name: 'Dowdall (Nauru)',
      summary: 'Like Borda, but ranks score 1, ½, ⅓… — the 1st choice weighs far more.',
      how: 'Each voter ranks everyone; rank k scores 1/(k+1) points. Sum them up.',
      strength: 'Strongly rewards top places without ignoring the rest of the ranking.',
      weakness: 'Arbitrary (harmonic) weights; breaks Borda’s reversal symmetry.',
      criterion: 'Positional like Borda but non-linear; fails Condorcet.',
      example: 'Used in Nauru: one 1st choice is worth two 2nd choices, three 3rd choices…',
    },
  },
  black: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Black (Condorcet-Borda)',
      summary: 'Le vainqueur de Condorcet s’il existe ; sinon, on bascule sur Borda.',
      how: 'On cherche qui bat tout le monde en duel ; à défaut (cycle), le score de Borda tranche.',
      strength: 'Le meilleur des deux mondes : Condorcet quand il existe, un repli robuste sinon.',
      weakness: 'Hérite des failles de Borda en cas de cycle ; échoue à la participation.',
      criterion: 'Condorcet-cohérent, monotone, respecte la majorité ; non strategy-proof.',
      example: 'Duncan Black (1958) : la solution la plus simple au problème des cycles.',
    },
    en: {
      name: 'Black (Condorcet-Borda)',
      summary: 'The Condorcet winner if one exists; otherwise fall back to Borda.',
      how: 'Look for who beats everyone head-to-head; if none (a cycle), the Borda score decides.',
      strength: 'Best of both worlds: Condorcet when it exists, a robust fallback otherwise.',
      weakness: 'Inherits Borda’s flaws on a cycle; fails participation.',
      criterion: 'Condorcet-consistent, monotone, meets majority; not strategyproof.',
      example: 'Duncan Black (1958): the simplest fix for the cycle problem.',
    },
  },
  smith_irv: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Smith-IRV (Tideman)',
      summary: 'On restreint au « Smith set », puis on élimine à la façon de l’IRV.',
      how: 'On garde le plus petit groupe qui bat tous les autres, on élimine le plus faible en 1ᵉʳˢ choix, et on recommence.',
      strength:
        'Élit toujours le vainqueur de Condorcet et résiste aux clones — le meilleur des deux mondes.',
      weakness: 'Non monotone (hérite de l’IRV) ; calcul plus lourd, moins lisible.',
      criterion: 'Condorcet-cohérent, indépendant des clones ; échoue à la monotonie.',
      example:
        'Souvent proposée comme réforme : la robustesse de Condorcet avec la dynamique de l’IRV.',
    },
    en: {
      name: 'Smith-IRV (Tideman)',
      summary: 'Restrict to the Smith set, then eliminate IRV-style.',
      how: 'Keep the smallest group that beats everyone else, eliminate the fewest first choices, repeat.',
      strength: 'Always elects the Condorcet winner and resists clones — the best of both worlds.',
      weakness: 'Non-monotone (inherits IRV); heavier to compute, less transparent.',
      criterion: 'Condorcet-consistent, clone-independent; fails monotonicity.',
      example: 'Often proposed as a reform: Condorcet robustness with IRV’s dynamics.',
    },
  },
  split_cycle: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Split Cycle',
      summary:
        'En cas de cycle, on écarte la victoire la plus faible ; le reste désigne le vainqueur.',
      how: 'Chaque défaite qui est le maillon faible d’un cycle est annulée ; gagne qui ne subit plus aucune défaite.',
      strength: 'Résout les cycles sans arbitraire ; solides garanties (immunité aux spoilers).',
      weakness: 'Peut désigner un ensemble (départage nécessaire) ; concept récent, peu connu.',
      criterion: 'Condorcet-cohérent, monotone, symétrie de révocation ; méthode par marges.',
      example:
        'Holliday & Pacuit (2021) : une alternative moderne à Schulze et aux paires ordonnées.',
    },
    en: {
      name: 'Split Cycle',
      summary: 'On a cycle, discard the weakest win; what remains picks the winner.',
      how: 'Any defeat that is the weakest link of a cycle is voided; whoever suffers no defeat wins.',
      strength: 'Resolves cycles without arbitrariness; strong guarantees (spoiler immunity).',
      weakness: 'Can return a set (needs a tie-break); recent, little-known concept.',
      criterion: 'Condorcet-consistent, monotone, reversal symmetry; a margin-based method.',
      example: 'Holliday & Pacuit (2021): a modern alternative to Schulze and ranked pairs.',
    },
  },
  cumulative: {
    family: 'cardinal',
    fr: {
      name: 'Vote cumulatif',
      summary: 'Chaque électeur répartit un budget de points entre les candidats comme il veut.',
      how: 'On distribue 1 point par électeur au prorata de ses préférences ; on somme les points.',
      strength: 'Laisse exprimer l’intensité et concentre le pouvoir des minorités motivées.',
      weakness: 'Fortement stratégique : tout mettre sur un seul candidat est souvent optimal.',
      criterion: 'Cardinal ; échoue à Condorcet et au critère de majorité.',
      example:
        'Élections de conseils d’administration ; défendu pour la représentation des minorités.',
    },
    en: {
      name: 'Cumulative voting',
      summary: 'Each voter spreads a budget of points across candidates however they like.',
      how: 'Give each voter 1 point split in proportion to their preferences; sum the points.',
      strength: 'Lets voters express intensity and concentrates the power of motivated minorities.',
      weakness: 'Highly strategic: piling everything on one candidate is often optimal.',
      criterion: 'Cardinal; fails Condorcet and the majority criterion.',
      example: 'Corporate board elections; advocated for minority representation.',
    },
  },
  maximin: {
    family: 'cardinal',
    fr: {
      name: 'Maximin (utilité)',
      summary:
        'On élit le candidat dont la PIRE note (chez l’électeur le plus déçu) est la moins mauvaise.',
      how: 'Pour chaque candidat, on regarde sa note la plus basse ; gagne le plus haut de ces minimums.',
      strength:
        'Critère rawlsien : protège l’électeur le plus mal servi, évite les vainqueurs clivants.',
      weakness: 'Ignore l’intensité moyenne ; un seul électeur très hostile peut tout décider.',
      criterion: 'Cardinal, égalitariste ; à l’opposé du score (utilitariste, qui somme).',
      example:
        'La justice comme équité (Rawls) appliquée au vote : le sort du plus faible d’abord.',
    },
    en: {
      name: 'Maximin (utility)',
      summary:
        'Elect the candidate whose WORST rating (from the unhappiest voter) is the least bad.',
      how: 'For each candidate take their lowest rating; the highest of those minimums wins.',
      strength: 'A Rawlsian criterion: protects the worst-served voter, avoids divisive winners.',
      weakness: 'Ignores average intensity; a single very hostile voter can decide everything.',
      criterion: 'Cardinal, egalitarian; the opposite of score voting (utilitarian sum).',
      example: 'Justice as fairness (Rawls) applied to voting: the worst-off voter first.',
    },
  },
  benham: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Benham (Condorcet-IRV)',
      summary: 'On déroule l’IRV, mais on s’arrête dès qu’un vainqueur de Condorcet apparaît.',
      how: 'À chaque tour : si un candidat bat tous les restants en duel, il est élu ; sinon on élimine le plus faible en 1ᵉʳˢ choix.',
      strength: 'Condorcet-cohérent tout en gardant la résistance aux clones de l’IRV.',
      weakness: 'Non monotone (hérite de l’IRV) ; très proche de Smith-IRV, moins connu.',
      criterion: 'Condorcet-cohérent, indépendant des clones ; échoue à la monotonie.',
      example: 'Une des façons les plus simples de « réparer » l’IRV pour respecter Condorcet.',
    },
    en: {
      name: 'Benham (Condorcet-IRV)',
      summary: 'Run IRV, but stop as soon as a Condorcet winner appears.',
      how: 'Each round: if a candidate beats all the rest head-to-head, elect them; otherwise drop the fewest first choices.',
      strength: 'Condorcet-consistent while keeping IRV’s clone resistance.',
      weakness: 'Non-monotone (inherits IRV); very close to Smith-IRV, less known.',
      criterion: 'Condorcet-consistent, clone-independent; fails monotonicity.',
      example: 'One of the simplest ways to “fix” IRV so it respects Condorcet.',
    },
  },
  river: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'River',
      summary:
        'Comme les paires ordonnées, mais chaque candidat n’a qu’un seul « verrou » entrant.',
      how: 'On verrouille les duels du plus net au plus serré, en sautant ceux qui bouclent un cycle ou visent un candidat déjà verrouillé ; la racine gagne.',
      strength:
        'Résultat en arbre, plus simple à auditer que Ranked Pairs, mêmes garanties Condorcet.',
      weakness: 'Peut différer des paires ordonnées ; méthode confidentielle.',
      criterion: 'Condorcet-cohérent, monotone, indépendant des clones ; par marges.',
      example: 'Heitzig (2004) : une variante « en rivière » des paires ordonnées de Tideman.',
    },
    en: {
      name: 'River',
      summary: 'Like ranked pairs, but each candidate takes only one incoming lock.',
      how: 'Lock duels from clearest to closest, skipping any that close a cycle or point at an already-locked candidate; the root wins.',
      strength:
        'A tree result, simpler to audit than ranked pairs, with the same Condorcet guarantees.',
      weakness: 'Can differ from ranked pairs; a niche method.',
      criterion: 'Condorcet-consistent, monotone, clone-independent; margin-based.',
      example: 'Heitzig (2004): a “river” variant of Tideman’s ranked pairs.',
    },
  },
  nash: {
    family: 'cardinal',
    fr: {
      name: 'Nash (produit d’utilités)',
      summary: 'On élit le candidat qui maximise le PRODUIT des notes, pas leur somme.',
      how: 'On multiplie les notes de tous les électeurs (moyenne géométrique) ; le plus haut produit gagne.',
      strength:
        'Équité proportionnelle : entre l’utilitarisme (score) et le maximin, pénalise les notes nulles.',
      weakness: 'Un seul électeur mettant 0 anéantit un candidat ; sensible à l’échelle des notes.',
      criterion: 'Cardinal ; le « bargaining » de Nash appliqué au vote — compromis somme/minimum.',
      example: 'Solution de Nash (1950) : le partage équitable qui multiplie les gains de chacun.',
    },
    en: {
      name: 'Nash (product of utilities)',
      summary: 'Elect the candidate maximising the PRODUCT of ratings, not their sum.',
      how: 'Multiply every voter’s rating (geometric mean); the highest product wins.',
      strength:
        'Proportional fairness: between utilitarian (score) and maximin, it punishes zeros.',
      weakness: 'A single 0 rating wipes out a candidate; sensitive to the rating scale.',
      criterion: 'Cardinal; Nash bargaining applied to voting — a sum/minimum compromise.',
      example: 'The Nash solution (1950): the fair split that multiplies everyone’s gains.',
    },
  },
  raynaud: {
    family: 'condorcet',
    condorcet: true,
    fr: {
      name: 'Raynaud',
      summary: 'On élimine à répétition le candidat qui subit la plus lourde défaite en duel.',
      how: 'On cherche la défaite de plus grande marge, on élimine le perdant, et on recommence.',
      strength:
        'Condorcet-cohérent : le vainqueur de Condorcet ne perd aucun duel, il survit toujours.',
      weakness: 'Non monotone ; se concentre sur les pires défaites plutôt que le bilan global.',
      criterion: 'Condorcet-cohérent ; méthode par élimination selon la pire défaite.',
      example: 'Une logique « à l’élimination directe » : le plus écrasé sort à chaque tour.',
    },
    en: {
      name: 'Raynaud',
      summary: 'Repeatedly eliminate the candidate on the losing end of the heaviest duel.',
      how: 'Find the largest-margin defeat, drop its loser, and repeat until one remains.',
      strength: 'Condorcet-consistent: the Condorcet winner loses no duel, so it always survives.',
      weakness: 'Non-monotone; focuses on worst defeats rather than the overall record.',
      criterion: 'Condorcet-consistent; elimination by the worst pairwise defeat.',
      example: 'A “knockout” logic: the most crushed candidate leaves each round.',
    },
  },
};

export type Lang = 'fr' | 'en';

export function getMethodInfo(id: string): MethodEntry | null {
  return METHOD_INFO[methodKey(id)] ?? null;
}

/**
 * Human-readable name for a method id (canonical or backend alias), in the given
 * language. Falls back to a prettified id (snake_case → Title Case) so raw
 * backend ids never leak into the UI.
 */
export function methodDisplayName(id: string, lang: Lang): string {
  const entry = METHOD_INFO[methodKey(id)];
  if (entry) return entry[lang].name;
  return id.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export interface MethodContext {
  /** Whether a Condorcet winner exists on the live electorate. */
  condorcetExists?: boolean;
}

/**
 * The "intelligent" bit: a short note tied to the live state. For the Condorcet
 * family, flags when no Condorcet winner currently exists (a cycle), so the card
 * explains the method is in its tie-break regime right now.
 */
export function methodContextNote(id: string, lang: Lang, ctx: MethodContext): string | null {
  const entry = METHOD_INFO[methodKey(id)];
  if (!entry?.condorcet) return null;
  if (ctx.condorcetExists === false) {
    return lang === 'en'
      ? 'Right now there is no Condorcet winner (the electorate cycles), so this method is in its tie-break regime.'
      : 'En ce moment il n’existe aucun vainqueur de Condorcet (l’électorat tourne en cycle) : la méthode est donc dans son régime de départage.';
  }
  return null;
}
