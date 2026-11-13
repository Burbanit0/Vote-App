import { describe, it, expect, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMethodLabels } from '../simulationConstants';
import { useUIStore } from '../../../stores/useUIStore';

// The simulation charts name methods with their own labels. In plain-language mode the rules the
// playground names plainly take that name here too (tests run in English).

afterEach(() => useUIStore.setState({ plainLanguage: false }));

describe('useMethodLabels', () => {
  it('uses the simulation’s own wording by default, and the playground’s for the other rules', () => {
    const { result } = renderHook(() => useMethodLabels());
    expect(result.current.plurality).toBe('Plurality');
    // A rule only the playground names: its technical label, not the raw slug.
    expect(result.current.nanson).toBe('Nanson');
    expect(result.current.ranked_pairs).toBe('Condorcet (ranked pairs)');
  });

  it('in plain-language mode, names the playground’s rules in plain words', () => {
    useUIStore.setState({ plainLanguage: true });
    const { result } = renderHook(() => useMethodLabels());
    expect(result.current.plurality).toBe('Most votes');
    expect(result.current.nanson).toBe('Drop the below-average');
    expect(result.current.ranked_pairs).toBe('Lock in the biggest wins');
  });

  it('keeps the label of an id only the simulation knows, plain mode or not', () => {
    const off = renderHook(() => useMethodLabels()).result.current.star_voting;
    useUIStore.setState({ plainLanguage: true });
    const on = renderHook(() => useMethodLabels()).result.current.star_voting;
    expect(off).toBeTruthy();
    expect(on).toBe(off);
  });
});
