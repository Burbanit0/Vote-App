import { describe, it, expect, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useVotingLabels } from './useVotingLabels';
import { useUIStore } from '../stores/useUIStore';

// Tests run in English (jsdom). Plain-language mode swaps a bounded set of method
// labels; everything else keeps its real term.

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

  it('on: a method with no plain label falls back to its technical name', () => {
    useUIStore.setState({ plainLanguage: true });
    const { result } = renderHook(() => useVotingLabels());
    expect(result.current.ruleLabels.kemeny).toBe('Kemeny-Young');
  });
});
