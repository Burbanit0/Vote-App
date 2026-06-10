import React from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { VIZ_COLORS } from './types';

/**
 * Shared Recharts bar chart for the per-method visualisations (Plurality,
 * Borda, IRV, …). Replaces the former Chart.js `<Bar>` — same look (per-bar
 * colour from VIZ_COLORS, optional title + y-axis label) with no chart.js
 * dependency. Animation is disabled so jsdom tests render synchronously.
 */
export interface MethodBarChartProps {
  labels: string[];
  values: number[];
  /** Series label shown in the tooltip. */
  seriesName?: string;
  /** Centered caption above the chart. */
  title?: string;
  /** Rotated y-axis title. */
  yLabel?: string;
  /** Fixed y-axis range, e.g. [0, 5] for score charts. Default: auto. */
  yDomain?: [number, number];
  /** Allow fractional y-axis ticks (for averages/scores). Default false. */
  allowDecimals?: boolean;
  /** Uniform bar colour. When omitted, each bar uses a VIZ_COLORS hue. */
  color?: string;
  height?: number;
}

const MethodBarChart: React.FC<MethodBarChartProps> = ({
  labels,
  values,
  seriesName = 'Votes',
  title,
  yLabel,
  yDomain,
  allowDecimals = false,
  color,
  height = 300,
}) => {
  const data = labels.map((label, i) => ({ label, value: values[i] ?? 0 }));

  return (
    <figure className="mb-0">
      {title && (
        <figcaption className="text-center font-semibold mb-2" style={{ fontSize: '0.95rem' }}>
          {title}
        </figcaption>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis
            allowDecimals={allowDecimals}
            domain={yDomain ?? [0, 'auto']}
            tick={{ fontSize: 12 }}
            label={
              yLabel
                ? { value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 12 } }
                : undefined
            }
          />
          <Tooltip />
          <Bar dataKey="value" name={seriesName} fill={color} isAnimationActive={false}>
            {!color &&
              data.map((_, i) => <Cell key={i} fill={VIZ_COLORS[i % VIZ_COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
};

export default MethodBarChart;
