import { renderHook, act } from '@testing-library/react';
import { useDebouncedCallback, DEBOUNCE_MS } from './useDebouncedCallback';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('useDebouncedCallback', () => {
  it('calls fn once, with the last arguments, after the delay', () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(fn));

    act(() => {
      result.current(1);
      result.current(2);
      result.current(3);
    });
    expect(fn).not.toHaveBeenCalled();

    act(() => void vi.advanceTimersByTime(DEBOUNCE_MS));
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith(3);
  });

  it('drops a pending call when the component unmounts', () => {
    // The regression this hook exists for: ten panels had no cleanup, so
    // leaving a Laboratoire fiche within 400ms of moving a slider still fired
    // the request at an unmounted panel.
    const fn = vi.fn();
    const { result, unmount } = renderHook(() => useDebouncedCallback(fn));

    act(() => result.current('pending'));
    unmount();
    act(() => void vi.advanceTimersByTime(DEBOUNCE_MS * 5));

    expect(fn).not.toHaveBeenCalled();
  });

  it('runs the newest closure, not the one captured when scheduling', () => {
    // The panels' fn closes over state the pending call has to see.
    const calls: number[] = [];
    const { result, rerender } = renderHook(({ n }) => useDebouncedCallback(() => calls.push(n)), {
      initialProps: { n: 1 },
    });

    act(() => result.current());
    rerender({ n: 2 });
    act(() => void vi.advanceTimersByTime(DEBOUNCE_MS));

    expect(calls).toEqual([2]);
  });

  it('honours a caller-supplied delay', () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(fn, 50));

    act(() => result.current());
    act(() => void vi.advanceTimersByTime(49));
    expect(fn).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(1));
    expect(fn).toHaveBeenCalledTimes(1);
  });
});
