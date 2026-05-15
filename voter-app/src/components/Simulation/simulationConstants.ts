import { useTranslation } from 'react-i18next';
import { SimulationCompareResult } from '../../types';

// WCAG 2.1 AA: all colours ≥ 4.5:1 on white and ≥ 4.5:1 on Bootstrap dark (#212529)
export const CANDIDATE_PALETTE = ['#1a56cc', '#b35c00', '#b71c1c', '#006957', '#1b5e20', '#544200'];

// Static keys — used as fallback IDs and in non-React contexts (report generation, CSV export)
export const METHOD_KEYS = [
  'plurality', 'two_round', 'borda', 'approval', 'irv', 'coombs', 'bucklin',
  'minimax', 'schulze', 'kemeny_young', 'condorcet', 'positional_score',
  'simple_score', 'star_voting', 'median_voting', 'mean_median_hybrid', 'variance_based',
  'quadratic',
] as const;

// Fallback labels used in non-React contexts (report HTML, CSV, buildConclusion)
export const METHOD_LABELS: Record<string, string> = {
  plurality:          'Plurality',
  two_round:          'Two-Round',
  borda:              'Borda',
  approval:           'Approval',
  irv:                'IRV',
  coombs:             "Coombs'",
  bucklin:            'Bucklin',
  minimax:            'Minimax',
  schulze:            'Schulze',
  kemeny_young:       'Kemeny-Young',
  condorcet:          'Condorcet',
  positional_score:   'Positional score',
  simple_score:       'Simple score',
  star_voting:        'STAR',
  median_voting:      'Median score',
  mean_median_hybrid: 'Mean-Median',
  variance_based:     'Variance-based',
  quadratic:          'Quadratic Vote',
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
  quadratic:      '#7c3aed',
};

export const STRATEGIC_PERCENTAGES = [0, 10, 20, 30, 40, 50];

// ── Translated method metadata hook ───────────────────────────────────────────
// Use this inside React components instead of the static constants below.

export function useMethodLabels(): Record<string, string> {
  const { t } = useTranslation();
  return Object.fromEntries(
    METHOD_KEYS.map((k) => [k, t(`methods.${k}.label`, { defaultValue: METHOD_LABELS[k] })])
  );
}

export function useMethodPros(): Record<string, string> {
  const { t } = useTranslation();
  return Object.fromEntries(
    METHOD_KEYS.map((k) => [k, t(`methods.${k}.pro`, { defaultValue: '' })])
  );
}

export function useMethodCons(): Record<string, string> {
  const { t } = useTranslation();
  return Object.fromEntries(
    METHOD_KEYS.map((k) => [k, t(`methods.${k}.con`, { defaultValue: '' })])
  );
}

// Descriptions stay in English (they're already English in the original constants)
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
  quadratic:
    'Each voter has a fixed credit budget (100). Casting v votes for a candidate costs v² credits. ' +
    'The optimal allocation is votes[c] ∝ √budget × utility[c] / Σutility. ' +
    'This exponential cost makes extreme preferences expensive, reducing the "tyranny of the majority" ' +
    'while allowing voters to express intensity. Proposed by Lalley & Weyl (2018) and popularised in "Radical Markets" (Posner & Weyl, 2018).',
};

// Keep static pros/cons as English fallbacks for non-React contexts
export const METHOD_PROS: Record<string, string> = {
  plurality:          'Simple and universally understood — one voter, one vote.',
  two_round:          'Ensures the winner faces a direct opponent in the runoff.',
  borda:              'Rewards broadly appreciated candidates, not just first choices.',
  approval:           'Eliminates the spoiler effect — approving multiple candidates penalises nobody.',
  irv:                'Guarantees a winner with majority support after successive eliminations.',
  coombs:             'Elects more centrist candidates than IRV by eliminating the most-rejected first.',
  bucklin:            'Ranking/approval hybrid that quickly converges to a majority winner.',
  minimax:            'The winner is the candidate whose worst pairwise defeat is the least bad.',
  schulze:            'Satisfies Condorcet, monotonicity and many other criteria — very robust.',
  kemeny_young:       'Theoretically optimal: maximises global consensus on the complete ranking.',
  condorcet:          'Elects the candidate who beats each other in a direct duel, if one exists.',
  positional_score:   'Assigns points by rank position — simple and expressive.',
  simple_score:       'Very expressive — voters nuance their support with numeric ratings.',
  star_voting:        'Combines score expressivity with resistance to polarisation via automatic runoff.',
  median_voting:      'Resistant to exaggeration — one extreme voter cannot shift the median as easily.',
  mean_median_hybrid: 'Balances the expressivity of the mean and robustness of the median (50/50).',
  variance_based:     'Penalises polarising candidates — favours broad and consistent support.',
  quadratic:          'Expresses preference intensity — voters allocate more credits to their strongly-felt choices, reducing majority tyranny.',
};

export const METHOD_CONS: Record<string, string> = {
  plurality:          'Creates the spoiler effect: a similar candidate can make your favourite lose.',
  two_round:          'Incentivises strategic voting in round 1 to "qualify".',
  borda:              'Vulnerable to "burial": deliberately ranking a rival last to minimise their score.',
  approval:           'The result depends on the approval threshold each voter sets for themselves.',
  irv:                'Non-monotone: promoting a candidate can paradoxically make them lose.',
  coombs:             'Sensitive to Condorcet cycles and counter-intuitive outcomes.',
  bucklin:            'Rarely used in practice and little studied empirically.',
  minimax:            'Does not always satisfy the Condorcet winner criterion.',
  schulze:            'Complex to explain to voters and hard to audit manually.',
  kemeny_young:       'Exponential O(n!) computation — unusable with 6 or more candidates.',
  condorcet:          'Does not always have a winner — cycles make the decision impossible.',
  positional_score:   'Result depends on the number of candidates (adding one shifts all scores).',
  simple_score:       'Dominant strategy is exaggeration: 5 to your favourite, 0 to everyone else.',
  star_voting:        'Less intuitive than classic voting — two steps to explain to voters.',
  median_voting:      'Can elect a candidate with a high median but few enthusiastic supporters.',
  mean_median_hybrid: 'The 50/50 weighting is arbitrary and hard to justify democratically.',
  variance_based:     'Counter-intuitive: a passionately loved candidate can be penalised.',
  quadratic:          'If credits can be purchased with money, wealthy voters gain disproportionate influence — equal budgets are essential.',
};

export const IDEOLOGY_OPTIONS = [
  { value: 'random',      labelKey: 'ideology.random' },
  { value: 'centrist',    labelKey: 'ideology.centrist' },
  { value: 'polarized',   labelKey: 'ideology.polarized' },
  { value: 'left_skewed', labelKey: 'ideology.left_skewed' },
  { value: 'right_skewed',labelKey: 'ideology.right_skewed' },
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
