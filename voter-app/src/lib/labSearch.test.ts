import { describe, expect, it } from 'vitest';
import { fold, hasWords, matchesQuery } from './labSearch';

describe('fold', () => {
  it('lower-cases and takes the accents off', () => {
    expect(fold('Électorat À Vous')).toBe('electorat a vous');
    expect(fold('Chevènement')).toBe('chevenement');
  });
});

describe('fold, ligatures', () => {
  it('spells them out, so "oeuvre" finds "œuvre"', () => {
    expect(fold('Cœur, œuvre, Æsop, Straße')).toBe('coeur, oeuvre, aesop, strasse');
    expect(matchesQuery('Une œuvre', 'oeuvre')).toBe(true);
  });
});

describe('hasWords', () => {
  it('is false for a blank, and for a lone accent (nothing left once accents are taken off)', () => {
    expect(hasWords('')).toBe(false);
    expect(hasWords('   ')).toBe(false);
    expect(hasWords('\u0301')).toBe(false);
  });

  it('is true as soon as one word is left', () => {
    expect(hasWords(' jury ')).toBe(true);
    expect(hasWords('é')).toBe(true);
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
