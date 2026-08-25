import React from 'react';

interface HemicycleLegendProps {
  seats: Record<string, number>;
  names: string[];
  colorFor: (name: string, names: string[]) => string;
  className?: string;
}

/** Party swatches below a hemicycle chart: one per party with seats, coloured
 * the same way as the wedge it corresponds to. */
const HemicycleLegend: React.FC<HemicycleLegendProps> = ({
  seats,
  names,
  colorFor,
  className = 'flex flex-wrap gap-1 justify-center',
}) => (
  <div className={className}>
    {names
      .filter((n) => (seats[n] ?? 0) > 0)
      .map((n) => (
        <span key={n} style={{ fontSize: '0.68rem' }}>
          <span
            style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              borderRadius: 1,
              background: colorFor(n, names),
              marginRight: 2,
            }}
          />
          {n} ({seats[n]})
        </span>
      ))}
  </div>
);

export default HemicycleLegend;
