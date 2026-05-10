import { useTheme } from '../context/ThemeContext';

/** Returns chart-safe colour values that adapt to light / dark mode. */
export function useChartTheme() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return {
    isDark,
    /** CartesianGrid stroke */
    gridStroke:   isDark ? '#495057' : '#e0e0e0',
    /** Axis tick text fill */
    tickFill:     isDark ? '#adb5bd' : '#666',
    /** Tooltip content panel */
    tooltipStyle: {
      backgroundColor: isDark ? '#2b3035' : '#fff',
      borderColor:     isDark ? '#495057' : '#dee2e6',
      color:           isDark ? '#dee2e6' : '#333',
    } as React.CSSProperties,
    /** Reference line stroke */
    refStroke:    isDark ? '#6c757d' : '#ccc',
  };
}
