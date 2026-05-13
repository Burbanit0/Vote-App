import React from 'react';
import { renderHook } from '@testing-library/react';
import { useChartTheme } from './useChartTheme';
import { ThemeProvider } from '../context/ThemeContext';

describe('useChartTheme', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>{children}</ThemeProvider>
  );

  it('returns expected theme object with palette keys', () => {
    const { result } = renderHook(() => useChartTheme(), { wrapper });
    expect(result.current).toHaveProperty('isDark');
    expect(result.current).toHaveProperty('gridStroke');
    expect(result.current).toHaveProperty('tickFill');
    expect(result.current).toHaveProperty('tooltipStyle');
    expect(result.current).toHaveProperty('refStroke');
  });

  it('returns light mode values by default', () => {
    const { result } = renderHook(() => useChartTheme(), { wrapper });
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
