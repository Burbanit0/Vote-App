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

export type MethodFamily = 'ordinal' | 'condorcet' | 'cardinal';

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
      example: 'Le playground bascule en approximation (KwikSort) au-delà de 6 candidats.',
    },
    en: {
      name: 'Kemeny-Young',
      summary: 'Finds the overall ranking that best agrees with every ballot.',
      how: 'Pick the order minimising total pairwise disagreement (Kendall-tau distance).',
      strength: 'Satisfies Condorcet and yields a full ranking, not just a winner.',
      weakness: 'Combinatorial cost (O(n!)): exact only up to ~6 candidates, else approximated.',
      criterion: 'Satisfies Condorcet and reversal symmetry; a “median consensus” optimum.',
      example: 'The playground switches to a KwikSort approximation beyond 6 candidates.',
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
};

export type Lang = 'fr' | 'en';

export function getMethodInfo(id: string): MethodEntry | null {
  return METHOD_INFO[methodKey(id)] ?? null;
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
