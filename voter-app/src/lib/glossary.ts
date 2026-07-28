// glossary — the missing lookup layer. Every notion the app throws at a newcomer
// (Condorcet, IRV, centre squeeze, VSE, valence, dépouillement…) gets ONE plain
// entry here, and — crucially — a "voir en action" deep-link into the live demo
// that shows it. Terms become the felt experience, not dead definitions.
//
// Why a co-located bilingual TS registry (like methodInfo.ts, not i18n keys):
// the copy is long-form domain-specific voting theory the maintainer tunes in one
// place; each entry carries fr/en and the component picks the language.
//
// seeInAction refs are VERIFIED URL mechanisms only (a test locks this):
//  · story → /playground?story=<id>   (StoryPlayer reads ?story=)
//  · lab   → /laboratoire?exp=<id>    (LaboratoirePage reads ?exp=)
//  · route → a real app route
// A term with no clean demo simply omits seeInAction — never fake a link.

export type SeeInAction =
  | { kind: 'story'; ref: string }
  | { kind: 'lab'; ref: string }
  | { kind: 'route'; ref: string };

export interface GlossaryCopy {
  /** Display term. */
  term: string;
  /** The gist, one line. */
  short: string;
  /** A sentence in plain language — concrete, no jargon. */
  plain: string;
}

export interface GlossaryEntry {
  fr: GlossaryCopy;
  en: GlossaryCopy;
  /** Deep-link to the demo that makes it felt (optional). */
  seeInAction?: SeeInAction;
}

/** Build the href for a "voir en action" link. */
export function seeInActionHref(s: SeeInAction): string {
  switch (s.kind) {
    case 'story':
      return `/playground?story=${s.ref}`;
    case 'lab':
      return `/laboratoire?exp=${s.ref}`;
    case 'route':
      return s.ref;
  }
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  condorcet: {
    fr: {
      term: 'Vainqueur de Condorcet',
      short: 'Celui qui bat tous les autres en duel.',
      plain:
        'Le candidat qui, comparé à chaque rival un contre un, gagne à chaque fois. Beaucoup de méthodes ne le choisissent pourtant pas.',
    },
    en: {
      term: 'Condorcet winner',
      short: 'The one who beats every rival head-to-head.',
      plain:
        'The candidate who wins every one-on-one match-up against the others. Many methods still fail to pick them.',
    },
    seeInAction: { kind: 'story', ref: 'paradox' },
  },
  'condorcet-cycle': {
    fr: {
      term: 'Paradoxe de Condorcet',
      short: 'A bat B, B bat C, C bat A — la majorité tourne en rond.',
      plain:
        'Parfois aucun candidat ne bat tous les autres : les préférences de la majorité forment une boucle. Il n’existe alors pas de « vrai » gagnant évident.',
    },
    en: {
      term: 'Condorcet paradox',
      short: 'A beats B, B beats C, C beats A — the majority loops.',
      plain:
        'Sometimes no candidate beats all the others: the majority’s preferences form a cycle, so there is no obvious "true" winner.',
    },
    seeInAction: { kind: 'story', ref: 'paradox' },
  },
  irv: {
    fr: {
      term: 'Vote alternatif (IRV)',
      short: 'On classe, puis on élimine le dernier tour par tour.',
      plain:
        'Vous classez les candidats. On élimine le moins bien placé et on reporte ses voix, jusqu’à un gagnant. Corrige souvent l’effet spoiler.',
    },
    en: {
      term: 'Instant-runoff (IRV)',
      short: 'You rank; the last-placed is eliminated round by round.',
      plain:
        'You rank the candidates. The lowest is eliminated and their votes transfer, until someone wins. Often cures the spoiler effect.',
    },
    seeInAction: { kind: 'story', ref: 'spoiler' },
  },
  spoiler: {
    fr: {
      term: 'Effet spoiler',
      short: 'Un candidat sans chance change quand même le gagnant.',
      plain:
        'Un troisième candidat, qui ne peut pas gagner, divise un camp et fait perdre celui qui aurait dû l’emporter. Le fléau de la pluralité.',
    },
    en: {
      term: 'Spoiler effect',
      short: 'A no-hope candidate still changes who wins.',
      plain:
        'A third candidate who cannot win splits one side’s vote and makes the would-be winner lose. Plurality’s classic flaw.',
    },
    seeInAction: { kind: 'story', ref: 'spoiler' },
  },
  'centre-squeeze': {
    fr: {
      term: 'Écrasement du centre',
      short: 'Le candidat que tous acceptent sort en premier.',
      plain:
        'Un centriste, préféré de peu de gens en premier choix mais accepté par tous, est éliminé d’emblée sous l’IRV — alors qu’il battrait chacun en duel.',
    },
    en: {
      term: 'Centre squeeze',
      short: 'The candidate everyone accepts is out first.',
      plain:
        'A centrist who is few people’s first choice but everyone’s acceptable one gets eliminated early under IRV — even though they’d beat each rival head-to-head.',
    },
    seeInAction: { kind: 'story', ref: 'squeeze' },
  },
  'vote-utile': {
    fr: {
      term: 'Vote utile',
      short: 'Voter contre son cœur pour ne pas « gâcher » sa voix.',
      plain:
        'Abandonner son favori pour un candidat mieux placé, de peur de faire gagner le pire. Certaines méthodes suppriment ce dilemme.',
    },
    en: {
      term: 'Lesser-evil voting',
      short: 'Voting against your heart so your vote isn’t "wasted".',
      plain:
        'Dropping your favourite for a stronger candidate, for fear of letting the worst win. Some methods remove this dilemma.',
    },
    seeInAction: { kind: 'story', ref: 'utile' },
  },
  valence: {
    fr: {
      term: 'Valence',
      short: 'La qualité d’un candidat, indépendante des idées.',
      plain:
        'Compétence, honnêteté, charisme — ce qui plaît à tous, quelle que soit la position idéologique. Peut séparer le favori du choix le meilleur pour le bien commun.',
    },
    en: {
      term: 'Valence',
      short: 'A candidate’s quality, apart from their ideas.',
      plain:
        'Competence, honesty, charisma — what everyone values regardless of ideology. It can split the front-runner from the choice best for overall welfare.',
    },
    seeInAction: { kind: 'story', ref: 'valence' },
  },
  plurality: {
    fr: {
      term: 'Pluralité (majorité relative)',
      short: 'Une croix ; le plus de voix gagne.',
      plain:
        'Chacun vote pour un seul nom, et celui qui en récolte le plus l’emporte — même sans dépasser 50 %. Le mode le plus simple, et le plus sensible au spoiler.',
    },
    en: {
      term: 'Plurality (first-past-the-post)',
      short: 'One mark; most votes wins.',
      plain:
        'Everyone picks one name and whoever gets the most wins — even below 50%. The simplest rule, and the one most prone to spoilers.',
    },
    seeInAction: { kind: 'story', ref: 'spoiler' },
  },
  borda: {
    fr: {
      term: 'Méthode Borda',
      short: 'Des points selon le rang ; le consensus gagne.',
      plain:
        'Chaque rang donne des points (1er = plus de points). Récompense les candidats larges plutôt que clivants — souvent un centriste.',
    },
    en: {
      term: 'Borda count',
      short: 'Points by rank; the consensus candidate wins.',
      plain:
        'Each rank awards points (1st = most). Rewards broadly-liked candidates over polarising ones — often a centrist.',
    },
    seeInAction: { kind: 'story', ref: 'five' },
  },
  approval: {
    fr: {
      term: 'Vote par approbation',
      short: 'Cochez tous ceux que vous acceptez.',
      plain:
        'Pas de classement : vous approuvez autant de candidats que vous voulez, et le plus approuvé gagne. En 2017, aurait rebattu tout l’ordre.',
    },
    en: {
      term: 'Approval voting',
      short: 'Tick everyone you find acceptable.',
      plain:
        'No ranking: you approve as many candidates as you like, and the most-approved wins. In France 2017 it would have reshuffled the whole field.',
    },
    seeInAction: { kind: 'lab', ref: 'res-real-election' },
  },
  score: {
    fr: {
      term: 'Vote par note',
      short: 'Notez chaque candidat, la meilleure moyenne gagne.',
      plain:
        'Vous donnez une note à chacun (comme 1 à 5). La plus haute moyenne l’emporte. « Sincère » y est déjà un choix : où placer le curseur ?',
    },
    en: {
      term: 'Score voting',
      short: 'Rate each candidate; best average wins.',
      plain:
        'You give every candidate a grade (say 1–5); the highest average wins. Even "honest" is a choice here: where do you set the scale?',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
  cumulative: {
    fr: {
      term: 'Vote cumulatif (points)',
      short: 'Répartissez un budget de points.',
      plain:
        'Vous avez un stock de points à distribuer entre les candidats — tout sur un seul, ou étalé. Concentrer ou répartir est déjà une stratégie.',
    },
    en: {
      term: 'Cumulative voting (points)',
      short: 'Spread a budget of points.',
      plain:
        'You get a pot of points to split among candidates — all on one, or spread out. Concentrating vs spreading is already a strategy.',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
  'ballot-language': {
    fr: {
      term: 'Langage de bulletin',
      short: 'La forme du bulletin décide ce qu’il peut dire.',
      plain:
        'Un nom, un ordre, des coches, des notes, des points : chaque forme ouvre ou ferme des méthodes. Votre avis ne change pas ; votre bulletin, si.',
    },
    en: {
      term: 'Ballot language',
      short: 'The ballot’s shape decides what it can say.',
      plain:
        'One name, a ranking, ticks, scores, points: each shape enables or forbids methods. Your opinion doesn’t change; your ballot does.',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
  depouillement: {
    fr: {
      term: 'Dépouillement',
      short: 'Compter les bulletins jusqu’au vainqueur.',
      plain:
        'Le décompte, tour par tour ou duel par duel, qui transforme la pile de bulletins en un gagnant. Rejouable à la main pour tout voir.',
    },
    en: {
      term: 'The count (tally)',
      short: 'Counting the ballots down to a winner.',
      plain:
        'The tally — round by round or duel by duel — that turns the pile of ballots into a winner. Replayable by hand so nothing is hidden.',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
  vse: {
    fr: {
      term: 'VSE (satisfaction des électeurs)',
      short: 'À quel point le gagnant satisfait l’électorat.',
      plain:
        'Une note de 0 à 100 % : 100 = le meilleur candidat possible pour le bien commun, 0 = un tirage au sort. Mesure la qualité d’une méthode.',
    },
    en: {
      term: 'VSE (voter satisfaction)',
      short: 'How well the winner satisfies the electorate.',
      plain:
        'A 0–100% score: 100 = the best possible candidate for overall welfare, 0 = a random pick. It rates how good a method is.',
    },
    seeInAction: { kind: 'lab', ref: 'anchor-vse' },
  },
  gallagher: {
    fr: {
      term: 'Indice de Gallagher',
      short: 'L’écart entre les voix et les sièges.',
      plain:
        'Mesure la distorsion d’un scrutin : proche de 0 = les sièges reflètent fidèlement les voix ; élevé = de gros écarts (un parti sur-représenté).',
    },
    en: {
      term: 'Gallagher index',
      short: 'The gap between votes and seats.',
      plain:
        'Measures a system’s distortion: near 0 = seats mirror votes faithfully; high = big gaps (a party over-represented).',
    },
    seeInAction: { kind: 'story', ref: 'structures' },
  },
  threshold: {
    fr: {
      term: 'Seuil électoral',
      short: 'La barre en dessous de laquelle on n’a aucun siège.',
      plain:
        'Un parti sous le seuil (souvent 5 %) n’obtient rien : ses voix sont perdues et redistribuées. Le seuil peut aussi pousser au vote utile.',
    },
    en: {
      term: 'Electoral threshold',
      short: 'The bar below which you get no seats.',
      plain:
        'A party under the threshold (often 5%) gets nothing: its votes are wasted and redistributed. The bar can also push voters to defect.',
    },
    seeInAction: { kind: 'story', ref: 'seuil' },
  },
  proportional: {
    fr: {
      term: 'Représentation proportionnelle',
      short: 'Les sièges suivent la part des voix.',
      plain:
        'Chaque parti reçoit des sièges à hauteur de son score. L’assemblée devient un miroir de l’électorat — au prix de coalitions plus fréquentes.',
    },
    en: {
      term: 'Proportional representation',
      short: 'Seats track vote share.',
      plain:
        'Each party gets seats in proportion to its votes. The assembly mirrors the electorate — at the cost of more frequent coalitions.',
    },
    seeInAction: { kind: 'story', ref: 'structures' },
  },
  dhondt: {
    fr: {
      term: 'D’Hondt / Sainte-Laguë',
      short: 'Deux façons d’arrondir la proportionnelle.',
      plain:
        'Deux formules pour attribuer les derniers sièges : D’Hondt avantage les grands partis, Sainte-Laguë est plus équitable pour les petits. Même voix, autre assemblée.',
    },
    en: {
      term: 'D’Hondt / Sainte-Laguë',
      short: 'Two ways to round proportional seats.',
      plain:
        'Two formulas for the last seats: D’Hondt favours large parties, Sainte-Laguë is fairer to small ones. Same votes, different assembly.',
    },
    seeInAction: { kind: 'story', ref: 'diviseur' },
  },
  monotonicity: {
    fr: {
      term: 'Monotonie',
      short: 'Gagner plus de soutien ne devrait jamais nuire.',
      plain:
        'Une méthode est monotone si mieux classer un candidat ne peut pas le faire perdre. L’IRV échoue parfois : gagner des voix peut vous éliminer.',
    },
    en: {
      term: 'Monotonicity',
      short: 'More support should never hurt you.',
      plain:
        'A method is monotone if ranking a candidate higher can never make them lose. IRV sometimes fails: gaining votes can knock you out.',
    },
  },
  'strategic-voting': {
    fr: {
      term: 'Vote stratégique',
      short: 'Mentir sur ses préférences pour un meilleur résultat.',
      plain:
        'Voter autrement que sincèrement pour infléchir l’issue. Aucune méthode raisonnable n’y échappe totalement (Gibbard-Satterthwaite) — certaines résistent mieux.',
    },
    en: {
      term: 'Strategic voting',
      short: 'Misstating preferences for a better outcome.',
      plain:
        'Voting other than sincerely to sway the result. No reasonable method fully escapes it (Gibbard-Satterthwaite) — some resist far better.',
    },
    seeInAction: { kind: 'lab', ref: 'strat-sincerity' },
  },
  quota: {
    fr: {
      term: 'Quota (Hare, Droop)',
      short: 'Le nombre de voix qui « achète » un siège.',
      plain:
        'Dans les scrutins à sièges multiples, le seuil de voix garantissant un élu. Les voix au-delà du quota sont reportées, pas gaspillées.',
    },
    en: {
      term: 'Quota (Hare, Droop)',
      short: 'The votes that "buy" one seat.',
      plain:
        'In multi-seat elections, the vote count that secures a seat. Votes beyond the quota transfer onward rather than being wasted.',
    },
    seeInAction: { kind: 'lab', ref: 'sys-stv' },
  },
  stv: {
    fr: {
      term: 'Vote unique transférable (STV)',
      short: 'La proportionnelle par le classement, sans partis.',
      plain:
        'On classe des personnes ; les voix en excès et celles des éliminés sont reportées jusqu’à remplir les sièges. Une assemblée proportionnelle sans listes.',
    },
    en: {
      term: 'Single transferable vote (STV)',
      short: 'Proportional representation by ranking, no party lists.',
      plain:
        'You rank people; surplus votes and eliminated candidates’ votes transfer until the seats fill. A proportional assembly without party lists.',
    },
    seeInAction: { kind: 'lab', ref: 'sys-stv' },
  },
  abstention: {
    fr: {
      term: 'Abstention / vote blanc',
      short: 'Ne pas choisir — et ce que ça pèse.',
      plain:
        'L’abstention retire votre bulletin du décompte ; le vote blanc, lui, peut compter comme un refus explicite selon les règles. Deux silences très différents.',
    },
    en: {
      term: 'Abstention / blank vote',
      short: 'Not choosing — and what that weighs.',
      plain:
        'Abstaining removes your ballot from the count; a blank vote can instead count as an explicit refusal, depending on the rules. Two very different silences.',
    },
    seeInAction: { kind: 'lab', ref: 'thy-blank' },
  },
  vote_blanc: {
    fr: {
      term: 'Vote blanc',
      short: 'Un refus exprimé — mais compté comment ?',
      plain:
        'Une enveloppe vide déposée volontairement : « aucun de ceux-là ». Selon le pays, il est ignoré, intégré aux exprimés, ou peut même annuler l’élection. La règle de comptage décide de son poids.',
    },
    en: {
      term: 'Blank vote',
      short: 'An expressed refusal — but counted how?',
      plain:
        'An empty envelope cast on purpose: "none of these". Depending on the country it is ignored, folded into the expressed votes, or can even annul the election. The counting rule decides its weight.',
    },
    seeInAction: { kind: 'lab', ref: 'thy-blank' },
  },
  pivotality: {
    fr: {
      term: 'Poids d’une voix (pivot)',
      short: 'La chance que votre voix fasse basculer.',
      plain:
        'Une voix ne compte vraiment que si elle départage. Ce poids ne dépend pas du nombre d’électeurs mais de l’écart entre les deux premiers.',
    },
    en: {
      term: 'Pivotality (weight of a vote)',
      short: 'The chance your vote is the tie-breaker.',
      plain:
        'A vote only truly counts if it decides. That weight depends not on the number of voters but on the gap between the top two.',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
  'two-round': {
    fr: {
      term: 'Scrutin à deux tours',
      short: 'Les deux premiers se départagent au second tour.',
      plain:
        'Si personne n’a la majorité, un second tour oppose les deux mieux placés. Peut éliminer un centriste qui aurait battu chacun en duel.',
    },
    en: {
      term: 'Two-round runoff',
      short: 'The top two face off in a second round.',
      plain:
        'If no one has a majority, a runoff pits the top two against each other. Can eliminate a centrist who would beat each rival head-to-head.',
    },
    seeInAction: { kind: 'route', ref: '/a-vous-de-jouer' },
  },
};
