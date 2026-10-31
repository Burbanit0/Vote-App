import { StrictMode, useEffect } from 'react';
import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useFrameLoop } from './useFrameLoop';

afterEach(() => vi.restoreAllMocks());

describe('useFrameLoop', () => {
  it('runs until the step returns false, and a kick while running is a no-op', () => {
    const frames: FrameRequestCallback[] = [];
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => frames.push(cb));
    const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
    let left = 2;
    const step = vi.fn(() => --left > 0);
    const { result, unmount } = renderHook(() => useFrameLoop(step));
    result.current();
    result.current();
    expect(frames).toHaveLength(1);
    frames.shift()!(16);
    frames.shift()!(32);
    expect(step).toHaveBeenCalledTimes(2);
    expect(frames).toHaveLength(0);
    result.current();
    expect(frames).toHaveLength(1);
    unmount();
    expect(cancel).toHaveBeenCalled();
  });

  it('starts again after StrictMode unmounts and remounts it', () => {
    const frames = new Map<number, FrameRequestCallback>();
    let id = 0;
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      frames.set(++id, cb);
      return id;
    });
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((n) => void frames.delete(n));
    renderHook(
      () => {
        const kick = useFrameLoop(() => false);
        useEffect(() => kick(), [kick]);
      },
      { wrapper: StrictMode }
    );
    expect(frames.size).toBe(1);
  });

  it('is not left stuck by a step that throws', () => {
    const frames: FrameRequestCallback[] = [];
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => frames.push(cb));
    const step = vi.fn(() => {
      throw new Error('boom');
    });
    const { result } = renderHook(() => useFrameLoop(step));
    result.current();
    expect(() => frames.shift()!(16)).toThrow('boom');
    result.current();
    expect(frames).toHaveLength(1);
  });
});
