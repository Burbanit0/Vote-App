import { describe, it, expect, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useVotingLabels } from './useVotingLabels';
import { useUIStore } from '../stores/useUIStore';
import { RULE_LABELS, type Rule } from '../lib/playgroundVoting';
import pgEn from '../i18n/locales/playground.en';
import pgFr from '../i18n/locales/playground.fr';

// Tests run in English (jsdom). Plain-language mode swaps every method's technical name for a
// plain one; the others' wording is locked here, rule by rule, in both languages.

afterEach(() => useUIStore.setState({ plainLanguage: false }));

describe('useVotingLabels — plain-language mode', () => {
  it('default (off): shows the real, technical method names', () => {
    useUIStore.setState({ plainLanguage: false });
    const { result } = renderHook(() => useVotingLabels());
    expect(result.current.ruleLabels.condorcet).toBe('Condorcet (Copeland)');
    expect(result.current.ruleLabels.plurality).toBe('Plurality (1 round)');
  });

  it('on: swaps the common methods for plain labels', () => {
    useUIStore.setState({ plainLanguage: true });
    const { result } = renderHook(() => useVotingLabels());
    expect(result.current.ruleLabels.condorcet).toBe('Best in duels');
    expect(result.current.ruleLabels.plurality).toBe('Most votes');
    expect(result.current.ruleLabels.irv).toBe('Round-by-round');
  });

  it('on: a method that used to keep its technical name now has a plain one', () => {
    useUIStore.setState({ plainLanguage: true });
    const { result } = renderHook(() => useVotingLabels());
    expect(result.current.ruleLabels.kemeny).toBe('Best overall ranking');
    expect(result.current.ruleLabels.nanson).toBe('Drop the below-average');
    expect(result.current.ruleLabels.random_ballot).toBe('Draw a ballot at random');
  });

  it('on: every rule is renamed, and none of them to its own technical name', () => {
    const rules = Object.keys(RULE_LABELS) as Rule[];
    useUIStore.setState({ plainLanguage: false });
    const technical = renderHook(() => useVotingLabels()).result.current.ruleLabels;
    useUIStore.setState({ plainLanguage: true });
    const plain = renderHook(() => useVotingLabels()).result.current.ruleLabels;
    for (const r of rules) expect(plain[r], r).not.toBe(technical[r]);
  });
});

describe.each([
  ['English', pgEn],
  ['French', pgFr],
])('rulesPlain, %s', (_name, locale) => {
  const plain = locale.rulesPlain as Record<string, string>;
  const rules = Object.keys(RULE_LABELS).sort();

  it('names exactly the engine’s rules: none missing, none left over from a removed one', () => {
    expect(Object.keys(plain).sort()).toEqual(rules);
  });

  it('gives no two rules the same plain name (they would be indistinguishable on screen)', () => {
    const names = Object.values(plain);
    expect(new Set(names).size).toBe(names.length);
  });

  it('names every rule differently from its technical name, in this language too', () => {
    const technical = locale.rules as Record<string, string>;
    for (const rule of rules) expect(plain[rule], rule).not.toBe(technical[rule]);
  });

  // 34 characters: the longest plain name (French) still sits on one line of the Méthode panel's
  // checkbox column with all 29 rules ticked (checked in a render, 2026-11-12).
  it('keeps each name to a line of the Méthode panel and of the footer (34 characters)', () => {
    for (const [rule, name] of Object.entries(plain)) {
      expect(name.length, `${rule}: ${name}`).toBeLessThanOrEqual(34);
      expect(name.trim(), rule).not.toBe('');
    }
  });
});
