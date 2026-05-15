export interface QuizQuestion {
  id: number;
  question: string;
  context?: string;
  options: string[];
  correctIndex: number;
  explanation: string;
  method?: string;
  difficulty: 'débutant' | 'intermédiaire' | 'expert';
}

const questions: QuizQuestion[] = [
  // ── Débutant ─────────────────────────────────────────────────────────────
  {
    id: 1,
    question: 'Lors d\'une élection à 3 candidats, A obtient 40 %, B 35 %, C 25 %. Qui est élu en scrutin uninominal à un tour ?',
    options: ['A, car il a le plus de voix', 'B, car il est au centre', 'C est éliminé, A et B vont au second tour', 'Personne — aucun n\'atteint 50 %'],
    correctIndex: 0,
    explanation: 'Le scrutin uninominal à un tour (pluralité) désigne simplement le candidat ayant le plus grand nombre de voix, même sans majorité absolue. A gagne avec 40 % bien qu\'une majorité (60 %) ait voté contre lui — c\'est le principal reproche fait à cette méthode.',
    method: 'plurality',
    difficulty: 'débutant',
  },
  {
    id: 2,
    question: 'Dans un vote par approbation, combien de candidats un électeur peut-il approuver ?',
    options: ['Un seul (son préféré)', 'Exactement deux', 'Autant qu\'il le souhaite', 'La moitié du nombre de candidats, arrondie'],
    correctIndex: 2,
    explanation: 'C\'est la définition du vote par approbation : chaque électeur coche tous les candidats qu\'il "approuve" (il peut en cocher 0, 1, 2… jusqu\'au nombre total). Cela élimine l\'effet spoiler : approuver un candidat ne pénalise jamais un autre.',
    method: 'approval',
    difficulty: 'débutant',
  },
  {
    id: 3,
    question: 'À quoi sert le second tour dans un scrutin à deux tours ?',
    options: ['À départager deux ex aequo', 'À permettre à la majorité absolue de s\'exprimer', 'À éliminer les candidats extrémistes', 'À recalculer les points Borda'],
    correctIndex: 1,
    explanation: 'Si aucun candidat n\'obtient la majorité absolue (> 50 %) au premier tour, un second tour oppose les deux finalistes. Résultat : le vainqueur bat toujours son adversaire en face à face, garantissant un soutien majoritaire direct. Cela réduit l\'effet spoiler par rapport à la pluralité simple.',
    method: 'two_round',
    difficulty: 'débutant',
  },
  {
    id: 4,
    question: 'Qu\'est-ce qu\'un vote blanc ?',
    options: ['Un bulletin mal rempli, donc nul', 'Un vote exprimant un refus de tous les candidats proposés', 'Un vote pour le candidat indépendant', 'Un bulletin vierge qui n\'est pas compté'],
    correctIndex: 1,
    explanation: 'Le vote blanc est un acte civique délibéré : l\'électeur se déplace mais refuse tous les candidats. Il est distinct du vote nul (bulletin invalide). En France depuis 2014, les blancs sont comptés séparément mais n\'influencent pas le résultat. D\'autres règles constitutionnelles (seuil, majorité requise…) peuvent lui donner plus de pouvoir.',
    difficulty: 'débutant',
  },
  {
    id: 5,
    question: 'Quelle est la différence entre majorité absolue et majorité relative ?',
    options: ['La majorité absolue est toujours 50 %, la relative dépend du contexte', 'La majorité absolue exige > 50 % des suffrages, la relative exige seulement le plus de voix', 'Il n\'y a pas de différence : ce sont des synonymes', 'La majorité relative exige 2/3 des voix'],
    correctIndex: 1,
    explanation: 'La majorité absolue (> 50 %) garantit qu\'un candidat est préféré par la moitié de l\'électorat. La majorité relative (pluralité) désigne simplement qui a le plus de voix — un candidat peut être élu avec 25 % si les autres candidats fragmentent le reste. Pluralité = majorité relative.',
    difficulty: 'débutant',
  },
  {
    id: 6,
    question: 'Comment la méthode de Borda attribue-t-elle les points pour 4 candidats ?',
    context: 'Un électeur classe les 4 candidats A, B, C, D dans cet ordre.',
    options: ['A=4, B=3, C=2, D=1', 'A=3, B=2, C=1, D=0', 'A=1, B=1, C=0, D=0 (approbation)', 'A=4, B=0, C=0, D=0 (pluralité)'],
    correctIndex: 1,
    explanation: 'Borda attribue n−1 points au premier choix, n−2 au second… 0 au dernier (n = nombre de candidats). Avec 4 candidats : A=3, B=2, C=1, D=0. Ces totaux récompensent les candidats largement appréciés, pas seulement les premiers choix.',
    method: 'borda',
    difficulty: 'débutant',
  },
  {
    id: 7,
    question: 'Qu\'est-ce que l\'effet spoiler ?',
    options: ['Quand un candidat révèle des informations confidentielles', 'Quand un troisième candidat similaire fait perdre son rival en divisant les voix', 'Quand les résultats sont annoncés avant la fermeture des bureaux', 'Quand un candidat retire sa candidature au dernier moment'],
    correctIndex: 1,
    explanation: 'L\'effet spoiler (ou vote utile) survient quand un candidat C, proche idéologiquement de A, prend assez de voix à A pour que B gagne. Exemple : en 2000 aux USA, Nader (Verts) aurait coûté la victoire à Gore face à Bush. La pluralité est la méthode la plus vulnérable à cet effet.',
    method: 'plurality',
    difficulty: 'débutant',
  },

  // ── Intermédiaire ─────────────────────────────────────────────────────────
  {
    id: 8,
    question: 'Dans quel ordre est éliminé le premier candidat en scrutin préférentiel (IRV) ?',
    context: 'Trois candidats : Alice (40 % de premiers choix), Bob (35 %), Carol (25 %). Aucun n\'a la majorité.',
    options: ['Alice — elle a le moins de seconds choix', 'Bob — il est en milieu de classement', 'Carol — elle a le moins de premiers choix', 'L\'élimination se fait par tirage au sort'],
    correctIndex: 2,
    explanation: 'L\'IRV (Instant Runoff Voting) élimine à chaque tour le candidat avec le moins de premiers choix. Carol (25 %) est éliminée. Ses bulletins sont ensuite redistribués au second choix de chaque électeur l\'ayant votée. On recommence jusqu\'à ce qu\'un candidat dépasse 50 %.',
    method: 'irv',
    difficulty: 'intermédiaire',
  },
  {
    id: 9,
    question: 'Qu\'est-ce que le paradoxe de Condorcet ?',
    context: '3 candidats : A>B pour 40 % des électeurs, B>C pour 55 %, C>A pour 60 %.',
    options: ['A gagne car il a le plus de voix au total', 'Aucun vainqueur de Condorcet n\'existe — il y a un cycle A>B>C>A', 'B gagne car il bat les deux autres en duel direct', 'C gagne car sa victoire sur A est la plus large'],
    correctIndex: 1,
    explanation: 'Le paradoxe de Condorcet : les préférences collectives peuvent être non-transitives. Ici A bat B, B bat C, mais C bat A — formant un cycle (comme pierre-feuille-ciseau). Aucun "vainqueur de Condorcet" n\'existe. Cela pose un problème fondamental à toutes les méthodes de vote basées sur les préférences.',
    method: 'condorcet',
    difficulty: 'intermédiaire',
  },
  {
    id: 10,
    question: 'Que se passe-t-il si le vote blanc dépasse 30 % sous la règle THRESHOLD_30 ?',
    options: ['Le vote blanc est élu et forme un gouvernement provisoire', 'L\'élection est invalidée et de nouvelles candidatures sont requises', 'Le candidat en tête gagne malgré tout', 'Les voix blanches sont redistribuées proportionnellement'],
    correctIndex: 1,
    explanation: 'Sous la règle THRESHOLD_30, si le vote blanc dépasse 30 % des suffrages, l\'élection tout entière est invalidée. Le message est constitutionnel : une majorité substantielle rejette l\'offre politique. De nouvelles élections avec de nouveaux candidats sont alors organisées. Cette règle donne au vote blanc un réel pouvoir de sanction.',
    difficulty: 'intermédiaire',
  },
  {
    id: 11,
    question: 'La méthode de Borda peut-elle élire un candidat qui perd tous ses duels directs ?',
    options: ['Non — Borda satisfait toujours le critère de Condorcet', 'Oui — les points Borda peuvent favoriser un candidat battu en duel par tous les autres', 'Seulement avec plus de 5 candidats', 'Seulement en cas d\'égalité parfaite'],
    correctIndex: 1,
    explanation: 'Borda ne satisfait pas le critère de Condorcet. Un candidat peut accumuler beaucoup de points Borda (souvent en deuxième position) sans jamais gagner de duel direct. À l\'inverse, un vainqueur de Condorcet peut perdre sous Borda s\'il polarise : adoré par certains, détesté par d\'autres. C\'est l\'une des failles documentées de Borda.',
    method: 'borda',
    difficulty: 'intermédiaire',
  },
  {
    id: 12,
    question: 'Qu\'est-ce que le vote stratégique (ou vote utile) ?',
    options: ['Voter pour son candidat préféré même s\'il n\'a pas de chances', 'Voter pour un candidat moins préféré pour éviter un résultat pire', 'Voter plusieurs fois dans des bureaux différents', 'Voter pour le candidat le plus riche'],
    correctIndex: 1,
    explanation: 'Le vote stratégique consiste à ne pas voter sincèrement pour son premier choix, car il semble non-viable, et à reporter son vote sur un candidat moins apprécié mais susceptible de battre le candidat détesté. "Voter utile" plutôt que "voter sincère". La pluralité est la méthode qui crée le plus d\'incitation au vote stratégique.',
    difficulty: 'intermédiaire',
  },
  {
    id: 13,
    question: 'Que garantit la règle MAJORITY_REQUIRED pour le vote blanc ?',
    options: ['Le vote blanc gagne si plus de la moitié des bulletins sont blancs', 'Le vainqueur doit obtenir plus de voix que le vote blanc en duel direct', 'Le vote blanc compte double dans le décompte final', 'Une majorité qualifiée (2/3) est requise pour tout candidat'],
    correctIndex: 1,
    explanation: 'Sous MAJORITY_REQUIRED, même si un candidat obtient le plus de voix, il ne peut être élu que s\'il bat le vote blanc en duel direct — c\'est-à-dire si une majorité d\'électeurs le préfère à "ne voter pour personne". Si le vote blanc gagne ce duel, l\'élection est invalidée. C\'est une forme de contrôle démocratique plus fine que le simple seuil.',
    difficulty: 'intermédiaire',
  },
  {
    id: 14,
    question: 'Quel critère le vainqueur de Condorcet satisfait-il toujours ?',
    options: ['Le critère de Pareto', 'Le critère de majorité (s\'il existe, il est élu par toute méthode cohérente)', 'Le critère de Borda', 'L\'indépendance aux alternatives non pertinentes (IIA)'],
    correctIndex: 0,
    explanation: 'Le vainqueur de Condorcet satisfait le critère de Pareto : si tout le monde préfère A à B, A ne peut pas perdre contre B. Plus précisément, le vainqueur de Condorcet bat chaque adversaire en duel direct, ce qui correspond exactement au critère de majorité par paires. Arrow a prouvé qu\'aucune méthode ne peut satisfaire tous les critères simultaneously avec 3+ candidats.',
    method: 'condorcet',
    difficulty: 'intermédiaire',
  },

  // ── Expert ────────────────────────────────────────────────────────────────
  {
    id: 15,
    question: 'Le théorème d\'impossibilité d\'Arrow (1951) démontre qu\'aucune méthode de vote classée ne peut satisfaire simultanément quels critères ?',
    options: ['Pareto, non-dictature, et indépendance aux alternatives non pertinentes (IIA)', 'Condorcet, Borda, et IRV simultanément', 'Majorité absolue, unanimité, et neutralité', 'Monotonie, réversibilité, et transitivité'],
    correctIndex: 0,
    explanation: 'Arrow a prouvé mathématiquement : pour 3+ candidats, toute méthode de vote doit violer au moins un de ces 3 critères : (1) Pareto — si tout le monde préfère A à B, B ne gagne pas ; (2) non-dictature — pas de votant dont les préférences dictent toujours le résultat ; (3) IIA — le classement entre A et B ne dépend pas des autres candidats. C\'est un résultat fondamental en théorie du choix social.',
    difficulty: 'expert',
  },
  {
    id: 16,
    question: 'Qu\'est-ce que le régret bayésien d\'une méthode de vote ?',
    options: ['La probabilité qu\'un électeur regrette son vote après l\'élection', 'La perte d\'utilité collective moyenne entre le vainqueur élu et le vainqueur optimal', 'Le nombre de candidats qui auraient battu le vainqueur en duel direct', 'L\'écart entre le score du vainqueur et la majorité absolue'],
    correctIndex: 1,
    explanation: 'Le régret bayésien mesure l\'insatisfaction collective : c\'est la différence entre l\'utilité maximale possible (si l\'électeur idéal gagnait) et l\'utilité réelle générée par le vainqueur élu, moyennée sur tous les électeurs et tous les scénarios. Une méthode à faible régret bayésien élit des candidats proches des préférences réelles de la population. Schulze, STAR et la médiane ont typiquement un régret plus faible que la pluralité.',
    difficulty: 'expert',
  },
  {
    id: 17,
    question: 'En quoi la méthode de Schulze diffère-t-elle de l\'IRV ?',
    options: ['Schulze n\'utilise pas les classements ; IRV si', 'Schulze trouve les chaînes de victoires pairwise les plus solides ; IRV élimine le moins bien classé à chaque tour', 'IRV satisfait le critère de Condorcet ; Schulze ne le satisfait pas', 'Schulze est applicable seulement à 2 candidats'],
    correctIndex: 1,
    explanation: 'IRV élimine séquentiellement le candidat avec le moins de premiers choix — un processus sensible à l\'ordre d\'élimination et non-monotone. Schulze calcule la "force" de chaque chemin de victoires en duels (algorithme Floyd-Warshall sur les préférences pairwise) et est monotone, satisfait Condorcet, Pareto et de nombreux autres critères. Schulze est utilisé par Debian, Wikimedia et d\'autres organisations.',
    method: 'schulze',
    difficulty: 'expert',
  },
  {
    id: 18,
    question: 'Comment fonctionne la méthode STAR (Score Then Automatic Runoff) ?',
    options: ['Les électeurs donnent 1 étoile à leur candidat préféré, le total décide', 'Phase 1 : scores 0–5 ; Phase 2 : les 2 meilleurs s\'affrontent en duel de préférences', 'Classement préférentiel puis élimination à la pluralité au dernier tour', 'Vote en deux tours : score au 1er, approbation au 2e'],
    correctIndex: 1,
    explanation: 'STAR combine l\'expressivité du score (0 à 5) avec la résistance à la polarisation du second tour automatique. Phase 1 : chaque électeur note chaque candidat ; les deux avec le meilleur total avancent. Phase 2 : sur les bulletins originaux, on compte qui préfère A ou B — la majorité décide. STAR réduit l\'incitation à l\'exagération (5-0-0) car le second tour se joue sur les préférences, pas les scores.',
    method: 'star_voting',
    difficulty: 'expert',
  },
  {
    id: 19,
    question: 'Qu\'est-ce que l\'indépendance aux alternatives non pertinentes (IIA) ?',
    options: ['Le classement entre A et B ne change pas si on ajoute ou retire un candidat C', 'Les candidats indépendants ne peuvent pas influencer le résultat', 'Une méthode ne dépend pas de l\'ordre de présentation des bulletins', 'Le résultat est indépendant de la taille de l\'électorat'],
    correctIndex: 0,
    explanation: 'IIA : si A bat B dans une élection, introduire ou retirer un candidat C (même très apprécié) ne devrait pas inverser le classement entre A et B. La pluralité viole massivement IIA — c\'est exactement l\'effet spoiler. Arrow a prouvé qu\'aucune méthode de classement ne peut toujours satisfaire IIA avec 3+ candidats. Certaines méthodes de score (approbation, vote de gamme) s\'en approchent davantage.',
    difficulty: 'expert',
  },
  {
    id: 20,
    question: 'Le théorème de Gibbard-Satterthwaite implique que toute méthode de vote déterministe est…',
    options: ['Équitable pour tous les électeurs', 'Soit dictatoriale, soit manipulable stratégiquement', 'Toujours convergente vers le vainqueur de Condorcet', 'Indépendante du nombre de candidats'],
    correctIndex: 1,
    explanation: 'Gibbard (1973) et Satterthwaite (1975) ont prouvé indépendamment : pour 3+ alternatives, toute méthode de vote déterministe (sans aléatoire) qui n\'est pas dictatoriale est "manipulable" — il existe toujours des situations où un électeur peut obtenir un meilleur résultat en mentant sur ses préférences. Cela généralise Arrow et explique pourquoi le vote stratégique est inévitable dans tout système.',
    difficulty: 'expert',
  },
];

export default questions;
