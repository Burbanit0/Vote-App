import { describe, expect, it } from 'vitest';
import { fold, matchesQuery } from './labSearch';

describe('fold', () => {
  it('lower-cases and takes the accents off', () => {
    expect(fold('Électorat À Vous')).toBe('electorat a vous');
    expect(fold('Chevènement')).toBe('chevenement');
  });
});

describe('matchesQuery', () => {
  it('matches everything for an empty or blank query', () => {
    expect(matchesQuery('Condorcet paradox', '')).toBe(true);
    expect(matchesQuery('Condorcet paradox', '   ')).toBe(true);
  });

  it('ignores case and accents on both sides', () => {
    expect(matchesQuery('Électorat composé', 'electorat')).toBe(true);
    expect(matchesQuery('Electorat compose', 'ÉLECTORAT')).toBe(true);
  });

  it('wants every word, in any order', () => {
    expect(matchesQuery('Vote blanc et abstention', 'blanc vote')).toBe(true);
    expect(matchesQuery('Vote blanc et abstention', 'blanc approbation')).toBe(false);
  });

  it('matches inside a word, not only at its start', () => {
    expect(matchesQuery('Gerrymandering', 'mander')).toBe(true);
  });

  it('finds nothing for a word that is not there', () => {
    expect(matchesQuery('Condorcet', 'borda')).toBe(false);
  });
});
