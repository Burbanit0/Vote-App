import {
  escapeLaTeX,
  generateLatexTable,
  generateBibtex,
  generateLatexReport,
  generateFullBibtex,
  SimulationExportParams,
} from './latexExport';
import { SimulationCompareResult } from '../types';
import { ScenarioConfig } from '../components/Simulation/simulationConstants';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  plurality: 'Pluralité',
  borda:     'Borda',
  schulze:   'Schulze',
};

const SINGLE_RESULT: SimulationCompareResult = {
  condorcet_winner: 'Alice',
  methods: {
    plurality: { winner: 'Alice', bayesian_regret: 0.12, condorcet_consistent: true, majority_satisfaction: 0.7, strategic_vulnerability: 0.3 },
    borda:     { winner: 'Bob',   bayesian_regret: 0.08, condorcet_consistent: false, majority_satisfaction: 0.8, strategic_vulnerability: 0.2 },
    schulze:   { winner: 'Alice', bayesian_regret: 0.06, condorcet_consistent: true,  majority_satisfaction: 0.75, strategic_vulnerability: 0.15 },
  },
};

// Three runs: Alice wins 2×, Bob wins 1×
const MULTI_RESULTS: SimulationCompareResult[] = [
  SINGLE_RESULT,
  {
    condorcet_winner: 'Alice',
    methods: {
      plurality: { winner: 'Alice', bayesian_regret: 0.11, condorcet_consistent: true, majority_satisfaction: 0.72, strategic_vulnerability: 0.28 },
      borda:     { winner: 'Alice', bayesian_regret: 0.07, condorcet_consistent: true, majority_satisfaction: 0.82, strategic_vulnerability: 0.18 },
      schulze:   { winner: 'Alice', bayesian_regret: 0.05, condorcet_consistent: true, majority_satisfaction: 0.77, strategic_vulnerability: 0.13 },
    },
  },
  {
    condorcet_winner: null,
    methods: {
      plurality: { winner: 'Bob',   bayesian_regret: 0.14, condorcet_consistent: false, majority_satisfaction: 0.65, strategic_vulnerability: 0.35 },
      borda:     { winner: 'Alice', bayesian_regret: 0.09, condorcet_consistent: null,  majority_satisfaction: 0.78, strategic_vulnerability: 0.22 },
      schulze:   { winner: 'Alice', bayesian_regret: 0.07, condorcet_consistent: null,  majority_satisfaction: 0.73, strategic_vulnerability: 0.17 },
    },
  },
];

const CONFIG: ScenarioConfig = {
  numVoters: 500,
  candidateInput: 'Alice, Bob, Charlie',
  ideology_distribution: 'random',
};

const PARAMS: SimulationExportParams = {
  config:         CONFIG,
  numSimulations: 10,
  methodCount:    3,
  date:           '2026-05-15',
  shareUrl:       'https://example.com/sim?cfg=abc123',
};

// ── escapeLaTeX ───────────────────────────────────────────────────────────────

describe('escapeLaTeX', () => {
  it('escapes underscore', () => {
    expect(escapeLaTeX('vote_blanc')).toBe('vote\\_blanc');
  });

  it('escapes ampersand', () => {
    expect(escapeLaTeX('Borda & Condorcet')).toBe('Borda \\& Condorcet');
  });

  it('escapes percent', () => {
    expect(escapeLaTeX('50%')).toBe('50\\%');
  });

  it('escapes dollar sign', () => {
    expect(escapeLaTeX('$100')).toBe('\\$100');
  });

  it('escapes hash', () => {
    expect(escapeLaTeX('#1')).toBe('\\#1');
  });

  it('escapes curly braces', () => {
    expect(escapeLaTeX('{test}')).toBe('\\{test\\}');
  });

  it('handles empty string', () => {
    expect(escapeLaTeX('')).toBe('');
  });

  it('does not modify plain text', () => {
    expect(escapeLaTeX('Alice wins')).toBe('Alice wins');
  });

  it('escapes multiple special chars in one string', () => {
    const result = escapeLaTeX('method_borda & 50%');
    expect(result).toContain('\\_');
    expect(result).toContain('\\&');
    expect(result).toContain('\\%');
  });
});

// ── generateLatexTable ────────────────────────────────────────────────────────

describe('generateLatexTable', () => {
  it('contains \\begin{tabular} and \\end{tabular}', () => {
    const out = generateLatexTable(SINGLE_RESULT ? [SINGLE_RESULT] : [], METHOD_LABELS);
    expect(out).toContain('\\begin{tabular}');
    expect(out).toContain('\\end{tabular}');
  });

  it('contains \\toprule and \\bottomrule (booktabs)', () => {
    const out = generateLatexTable([SINGLE_RESULT], METHOD_LABELS);
    expect(out).toContain('\\toprule');
    expect(out).toContain('\\bottomrule');
  });

  it('includes method labels', () => {
    const out = generateLatexTable([SINGLE_RESULT], METHOD_LABELS);
    expect(out).toContain('Pluralité');
    expect(out).toContain('Borda');
    expect(out).toContain('Schulze');
  });

  it('escapes underscores in method names', () => {
    const labelsWithUnderscore = { my_method: 'My_Method' };
    const result: SimulationCompareResult = {
      condorcet_winner: null,
      methods: {
        my_method: { winner: 'Alice', bayesian_regret: 0.1, condorcet_consistent: null, majority_satisfaction: null, strategic_vulnerability: null },
      },
    };
    const out = generateLatexTable([result], labelsWithUnderscore);
    expect(out).toContain('\\_');
    expect(out).not.toMatch(/(?<!\\)_/);  // no unescaped underscore
  });

  it('escapes ampersands in candidate names', () => {
    const result: SimulationCompareResult = {
      condorcet_winner: null,
      methods: {
        plurality: { winner: 'A & B', bayesian_regret: null, condorcet_consistent: null, majority_satisfaction: null, strategic_vulnerability: null },
      },
    };
    const out = generateLatexTable([result], { plurality: 'Pluralité' });
    expect(out).toContain('\\&');
  });

  it('returns a comment when results are empty', () => {
    const out = generateLatexTable([], METHOD_LABELS);
    expect(out).toContain('%');
  });

  it('includes the most common winner across multiple runs', () => {
    const out = generateLatexTable(MULTI_RESULTS, METHOD_LABELS);
    // Alice wins plurality 2/3 times
    expect(out).toContain('Alice');
  });

  it('includes the run count in the winner cell', () => {
    const out = generateLatexTable(MULTI_RESULTS, METHOD_LABELS);
    // Alice wins plurality 2 out of 3 runs
    expect(out).toMatch(/2\/3|3\/3/);
  });

  it('contains \\begin{table} environment', () => {
    const out = generateLatexTable([SINGLE_RESULT], METHOD_LABELS);
    expect(out).toContain('\\begin{table}');
    expect(out).toContain('\\end{table}');
  });
});

// ── generateBibtex ────────────────────────────────────────────────────────────

describe('generateBibtex', () => {
  it('starts with @misc{', () => {
    const out = generateBibtex(PARAMS);
    expect(out.trimStart()).toMatch(/^@misc\{/);
  });

  it('contains the year from the date param', () => {
    const out = generateBibtex(PARAMS);
    expect(out).toContain('2026');
  });

  it('contains candidate names in the title', () => {
    const out = generateBibtex(PARAMS);
    expect(out).toContain('Alice');
    expect(out).toContain('Bob');
    expect(out).toContain('Charlie');
  });

  it('contains voter count in note', () => {
    const out = generateBibtex(PARAMS);
    expect(out).toContain('500');
  });

  it('includes the shareUrl when provided', () => {
    const out = generateBibtex(PARAMS);
    expect(out).toContain('https://example.com');
  });

  it('omits url field when shareUrl is not provided', () => {
    const paramsNoUrl: SimulationExportParams = { ...PARAMS, shareUrl: undefined };
    const out = generateBibtex(paramsNoUrl);
    expect(out).not.toContain('url');
  });

  it('is a single entry (no double @misc)', () => {
    const out = generateBibtex(PARAMS);
    const count = (out.match(/@misc/g) ?? []).length;
    expect(count).toBe(1);
  });

  it('ends with closing brace', () => {
    const out = generateBibtex(PARAMS);
    expect(out.trim()).toMatch(/\}$/);
  });
});

// ── generateLatexReport ───────────────────────────────────────────────────────

describe('generateLatexReport', () => {
  it('contains \\begin{document}', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\begin{document}');
  });

  it('contains \\end{document}', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\end{document}');
  });

  it('contains \\documentclass', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\documentclass');
  });

  it('includes booktabs package', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\usepackage{booktabs}');
  });

  it('includes hyperref package', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\usepackage');
    expect(out).toContain('hyperref');
  });

  it('contains a results table', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\begin{table}');
    expect(out).toContain('\\end{table}');
  });

  it('references Arrow 1951', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('arrow1951');
  });

  it('includes candidate names in the document', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('Alice');
    expect(out).toContain('Bob');
  });

  it('returns a comment when results are empty', () => {
    const out = generateLatexReport(PARAMS, [], METHOD_LABELS);
    expect(out).toContain('%');
    expect(out).not.toContain('\\begin{document}');
  });

  it('includes bibliography section', () => {
    const out = generateLatexReport(PARAMS, MULTI_RESULTS, METHOD_LABELS);
    expect(out).toContain('\\begin{thebibliography}');
    expect(out).toContain('\\end{thebibliography}');
  });
});

// ── generateFullBibtex ────────────────────────────────────────────────────────

describe('generateFullBibtex', () => {
  it('contains entries for used methods', () => {
    const out = generateFullBibtex(['borda', 'schulze'], PARAMS);
    expect(out).toContain('borda1781');
    expect(out).toContain('schulze2011');
  });

  it('always includes Arrow and Gibbard', () => {
    const out = generateFullBibtex(['plurality'], PARAMS);
    expect(out).toContain('arrow1951');
    expect(out).toContain('gibbard1973');
  });

  it('contains the simulation entry', () => {
    const out = generateFullBibtex(['plurality'], PARAMS);
    expect(out).toMatch(/@misc\{votelab/);
  });

  it('has multiple @article and @book entries', () => {
    const out = generateFullBibtex(['borda', 'schulze', 'irv', 'approval'], PARAMS);
    const entryCount = (out.match(/@(misc|article|book|inproceedings)\{/g) ?? []).length;
    expect(entryCount).toBeGreaterThan(3);
  });
});
