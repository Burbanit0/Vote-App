import { SimulationCompareResult } from '../../types';

export const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

export const METHOD_LABELS: Record<string, string> = {
  plurality:          'Pluralité',
  two_round:          'Deux tours',
  borda:              'Borda',
  approval:           'Approbation',
  irv:                'IRV',
  coombs:             "Coombs'",
  bucklin:            'Bucklin',
  minimax:            'Minimax',
  schulze:            'Schulze',
  kemeny_young:       'Kemeny-Young',
  condorcet:          'Condorcet',
  positional_score:   'Score positionnel',
  simple_score:       'Score simple',
  star_voting:        'STAR',
  median_voting:      'Score médian',
  mean_median_hybrid: 'Moy.-Médiane',
  variance_based:     'Variance',
};

export const METHOD_LINE_COLORS: Record<string, string> = {
  plurality: '#e15759',
  two_round: '#f28e2b',
  borda: '#4e79a7',
  approval: '#76b7b2',
  irv: '#59a14f',
  coombs: '#edc948',
  bucklin: '#b07aa1',
  minimax: '#ff9da7',
  schulze: '#9c755f',
  kemeny_young: '#bab0ac',
  simple_score: '#86bcb6',
  star_voting: '#e05c5c',
  median_voting: '#499894',
  mean_median_hybrid: '#f1ce63',
  variance_based: '#d37295',
};

export const STRATEGIC_PERCENTAGES = [0, 10, 20, 30, 40, 50];

export const METHOD_PROS: Record<string, string> = {
  plurality:          'Simple et universellement compris — un électeur, une voix.',
  two_round:          'Garantit que le vainqueur affronte un adversaire direct au second tour.',
  borda:              'Récompense les candidats largement appréciés, pas seulement les premiers choix.',
  approval:           'Élimine l\'effet spoiler — approuver plusieurs candidats ne pénalise personne.',
  irv:                'Garantit un vainqueur avec soutien majoritaire après éliminations successives.',
  coombs:             'Élit des candidats plus centristes qu\'IRV en éliminant d\'abord le plus rejeté.',
  bucklin:            'Hybride classement/approbation qui converge rapidement vers un vainqueur majoritaire.',
  minimax:            'Le vainqueur est celui dont la pire défaite pairwise est la moins mauvaise.',
  schulze:            'Satisfait Condorcet, monotonie et de nombreux autres critères — très robuste.',
  kemeny_young:       'Théoriquement optimal : maximise le consensus global sur le classement complet.',
  condorcet:          'Élit le candidat qui bat chacun des autres en duel direct, s\'il existe.',
  positional_score:   'Attribue des points selon la position dans les classements — simple et expressif.',
  simple_score:       'Très expressif — les électeurs nuancent leur soutien avec des notes chiffrées.',
  star_voting:        'Combine expressivité du score et résistance à la polarisation via un second tour automatique.',
  median_voting:      'Résistant à l\'exagération — un électeur extrême ne déplace pas la médiane.',
  mean_median_hybrid: 'Equilibre l\'expressivité de la moyenne et la robustesse de la médiane (50/50).',
  variance_based:     'Pénalise les candidats polarisants — favorise un soutien large et régulier.',
};

export const METHOD_CONS: Record<string, string> = {
  plurality:          'Crée l\'effet spoiler : un candidat similaire peut faire perdre votre favori.',
  two_round:          'Incite au vote stratégique dès le premier tour pour "se qualifier".',
  borda:              'Vulnérable au "vote enterrement" : placer délibérément un rival en dernière position.',
  approval:           'Le résultat dépend du seuil d\'approbation que chaque électeur se fixe.',
  irv:                'Non-monotone : promouvoir un candidat peut paradoxalement le faire perdre.',
  coombs:             'Sensible aux cycles de Condorcet et aux résultats contre-intuitifs.',
  bucklin:            'Peu utilisé en pratique et peu étudié empiriquement.',
  minimax:            'Ne satisfait pas toujours le critère du vainqueur de Condorcet.',
  schulze:            'Complexe à expliquer aux électeurs et difficile à auditer manuellement.',
  kemeny_young:       'Calcul exponentiel O(n!) — inutilisable dès 6 candidats ou plus.',
  condorcet:          'N\'a pas toujours de vainqueur — les cycles rendent la décision impossible.',
  positional_score:   'Le résultat dépend du nombre de candidats (ajout d\'un candidat modifie les scores).',
  simple_score:       'La stratégie dominante est l\'exagération : 5 au préféré, 0 à tous les autres.',
  star_voting:        'Moins intuitif que le vote classique — deux étapes à expliquer aux électeurs.',
  median_voting:      'Peut élire un candidat avec médiane haute mais peu de supporters enthousiastes.',
  mean_median_hybrid: 'La pondération 50/50 est arbitraire et difficile à justifier démocratiquement.',
  variance_based:     'Contre-intuitif : un candidat aimé passionnément par certains peut être pénalisé.',
};

export const METHOD_DESCRIPTIONS: Record<string, string> = {
  plurality:
    'Each voter votes for one candidate; the most votes wins. Simple, but vulnerable to vote-splitting: a similar candidate entering the race can reverse the outcome (spoiler effect).',
  two_round:
    'If no candidate reaches a majority in round 1, the top two face a runoff. Reduces vote-splitting but still incentivises strategic voting in the first round.',
  borda:
    'Voters rank all candidates; each rank earns points (last = 0). Totals decide the winner. Rewards broad appeal, but susceptible to the "burial" strategy: placing a strong rival last to minimise their score.',
  approval:
    'Voters approve any number of candidates; the most-approved wins. Eliminates the spoiler effect. The strategic challenge is calibrating how many candidates to approve.',
  irv:
    'Instant Runoff Voting: the weakest candidate (fewest first choices) is eliminated each round until someone has a majority. Can still incentivise compromise voting when your preferred candidate is not viable.',
  coombs:
    "Like IRV but eliminates the candidate with the most last-place votes each round. Tends to elect more centrist winners than standard IRV.",
  bucklin:
    'Voters rank candidates. Approval is expanded rank-by-rank until a majority is reached. A hybrid between ranked and approval voting.',
  minimax:
    "Minimises the maximum pairwise opposition: the winner is the candidate whose worst head-to-head defeat is the least bad. A Condorcet-extension method.",
  schulze:
    'Finds the strongest chain of pairwise victories (Floyd–Warshall path strength). Satisfies Condorcet, monotonicity, and many other criteria. Widely used in online elections.',
  kemeny_young:
    'Finds the complete ranking minimising the total Kendall-tau distance from all voter rankings. Computationally expensive (O(n!) candidates) but theoretically very robust.',
  simple_score:
    'Voters assign a numeric score to each candidate; the highest average wins. High expressivity, but exaggeration (giving 5 to your favourite, 0 to the rest) is the dominant strategy.',
  star_voting:
    'Score Then Automatic Runoff: the two highest-scoring candidates face a pairwise runoff. Combines score expressivity with resistance to strategic polarisation.',
  median_voting:
    'The winner has the highest median score. Inherently resistant to exaggeration — one extreme voter cannot shift the median as easily as the mean.',
  mean_median_hybrid:
    '50 % mean + 50 % median composite score. Balances expressivity and resistance to strategic manipulation.',
  variance_based:
    'Score = mean − 0.5 × std_dev. Penalises polarising candidates who score high with some voters but low with others, favouring consistent broad support.',
};

export const IDEOLOGY_OPTIONS = [
  { value: 'random', label: 'Random' },
  { value: 'centrist', label: 'Centrist' },
  { value: 'polarized', label: 'Polarized' },
  { value: 'left_skewed', label: 'Left-skewed' },
  { value: 'right_skewed', label: 'Right-skewed' },
];

export interface ScenarioConfig {
  numVoters: number;
  candidateInput: string;
  ideology_distribution: string;
}

export function mostCommonWinner(results: SimulationCompareResult[], method: string): string | null {
  const winners = results
    .map((r) => r.methods[method]?.winner)
    .filter((w): w is string => !!w);
  if (!winners.length) return null;
  const counts = winners.reduce(
    (acc, w) => ({ ...acc, [w]: (acc[w] ?? 0) + 1 }),
    {} as Record<string, number>
  );
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}
