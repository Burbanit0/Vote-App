import { renderHook } from '@testing-library/react';
import { useChartTheme } from './useChartTheme';

describe('useChartTheme', () => {
  // Theme is store-backed (useUIStore) — no provider needed.

  it('returns expected theme object with palette keys', () => {
    const { result } = renderHook(() => useChartTheme());
    expect(result.current).toHaveProperty('isDark');
    expect(result.current).toHaveProperty('gridStroke');
    expect(result.current).toHaveProperty('tickFill');
    expect(result.current).toHaveProperty('tooltipStyle');
    expect(result.current).toHaveProperty('refStroke');
  });

  it('returns light mode values by default', () => {
    const { result } = renderHook(() => useChartTheme());
    expect(result.current.isDark).toBe(false);
    expect(result.current.gridStroke).toBe('#e0e0e0');
    expect(result.current.tickFill).toBe('#666');
    expect(result.current.refStroke).toBe('#ccc');
    expect(result.current.tooltipStyle).toEqual({
      backgroundColor: '#fff',
      borderColor: '#dee2e6',
      color: '#333',
    });
  });
});
