import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useMediaQuery, useReducedMotion } from './useMediaQuery';

const original = window.matchMedia;
afterEach(() => {
  window.matchMedia = original;
});

function fakeMedia(initial: boolean) {
  const mq = {
    matches: initial,
    listeners: [] as (() => void)[],
    addEventListener: vi.fn((_: string, fn: () => void) => mq.listeners.push(fn)),
    removeEventListener: vi.fn(),
  };
  window.matchMedia = vi.fn(() => mq) as unknown as typeof window.matchMedia;
  return mq;
}

describe('useMediaQuery', () => {
  it('reports the query and follows its changes', () => {
    const mq = fakeMedia(false);
    const { result, unmount } = renderHook(() => useMediaQuery('(min-width: 1px)'));
    expect(result.current).toBe(false);
    mq.matches = true;
    act(() => mq.listeners.forEach((fn) => fn()));
    expect(result.current).toBe(true);
    unmount();
    expect(mq.removeEventListener).toHaveBeenCalled();
  });

  it('reads prefers-reduced-motion', () => {
    fakeMedia(true);
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(true);
    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)');
  });
});
