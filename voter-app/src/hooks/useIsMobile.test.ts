import { renderHook, act } from '@testing-library/react';
import { useIsMobile } from './useIsMobile';

describe('useIsMobile', () => {
  beforeEach(() => {
    window.innerWidth = 1024;
  });

  it('returns isMobile=false for default jsdom width (1024)', () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it('returns isMobile=true when innerWidth=500', () => {
    window.innerWidth = 500;
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it('returns isMobile=false when innerWidth=1024', () => {
    window.innerWidth = 1024;
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it('updates value on window resize', () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);

    act(() => {
      window.innerWidth = 500;
      window.dispatchEvent(new Event('resize'));
    });
    expect(result.current).toBe(true);

    act(() => {
      window.innerWidth = 1024;
      window.dispatchEvent(new Event('resize'));
    });
    expect(result.current).toBe(false);
  });

  it('uses custom breakpoint', () => {
    window.innerWidth = 900;
    const { result } = renderHook(() => useIsMobile(900));
    expect(result.current).toBe(false);

    act(() => {
      window.innerWidth = 899;
      window.dispatchEvent(new Event('resize'));
    });
    expect(result.current).toBe(true);
  });
});
