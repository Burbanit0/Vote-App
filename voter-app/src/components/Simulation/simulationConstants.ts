import { SimulationCompareResult } from '../../types';

export const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

export const METHOD_LABELS: Record<string, string> = {
  plurality: 'Plurality',
  two_round: 'Two-Round',
  borda: 'Borda',
  approval: 'Approval',
  irv: 'IRV',
  coombs: "Coombs'",
  bucklin: 'Bucklin',
  minimax: 'Minimax',
  schulze: 'Schulze',
  kemeny_young: 'Kemeny-Young',
  simple_score: 'Simple Score',
  star_voting: 'STAR',
  median_voting: 'Median Score',
  mean_median_hybrid: 'Mean-Median',
  variance_based: 'Variance-Based',
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
