import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, afterEach } from 'vitest';
import ResultsMethodTable from '../ResultsMethodTable';
import { methodDisplayName } from '../../../../lib/methodInfo';
import { useUIStore } from '../../../../stores/useUIStore';
import type { ElectionResult } from '../../../../services/electionApi';

// The playground's full-results table lists the engine's methods by their backend ids. In
// plain-language mode the ids that are engine rules take their plain name; any other id keeps its
// own name (tests run in English).

const row = { winner: 'Alice', bayesian_regret: 0.1, condorcet_consistent: true };
const result = {
  config: { blank_vote: { enabled: false } },
  candidates: [{ name: 'Alice', x: 0, y: 0, party: 'Green' }],
  methods: { plurality: row, borda: row, star_voting: row },
  condorcet_winner: 'Alice',
  blank_rate: 0,
  campaign_trajectory: null,
  inter_method_agreement: 1,
  condorcet_exists: true,
  voters_snapshot: [],
} as unknown as ElectionResult;

afterEach(() => useUIStore.setState({ plainLanguage: false }));

const methodCells = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((tr) => tr.querySelector('td')?.textContent ?? '');

describe('ResultsMethodTable — method names', () => {
  it('shows the methods’ own names by default', () => {
    render(<ResultsMethodTable result={result} />);
    const [borda, plurality, star] = methodCells();
    expect(borda).toContain(methodDisplayName('borda', 'en'));
    expect(plurality).toContain(methodDisplayName('plurality', 'en'));
    expect(star).toContain(methodDisplayName('star_voting', 'en'));
  });

  it('in plain-language mode names the engine’s rules in plain words, and only those', () => {
    useUIStore.setState({ plainLanguage: true });
    render(<ResultsMethodTable result={result} />);
    const [borda, plurality, star] = methodCells();
    expect(borda).toContain('Points by rank');
    expect(plurality).toContain('Most votes');
    // An id that is not one of the engine's rules is not renamed.
    expect(star).toContain(methodDisplayName('star_voting', 'en'));
    expect(star).not.toContain('Rate, then duel');
  });
});
