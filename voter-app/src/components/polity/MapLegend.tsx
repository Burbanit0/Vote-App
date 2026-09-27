import React from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { MAP_COLORS, type LegendEntry, type PointShape } from '../../lib/polity/mapScene';

/** A legend key as text: party keys carry their number, the others have a label. */
export function legendLabel(t: TFunction<'polity'>, key: string): string {
  const party = /^party(\d+)$/.exec(key);
  return party
    ? t('map.partyLegend', { id: party[1] })
    : t(`map.legend.${key}`, { defaultValue: key });
}

const SWATCH_PATHS: Record<PointShape, string> = {
  circle: 'M6,2 A4,4 0 1,1 5.99,2 Z',
  ring: 'M6,2 A4,4 0 1,1 5.99,2 Z',
  square: 'M2,2 H10 V10 H2 Z',
  triangle: 'M6,1.5 L10.5,10 L1.5,10 Z',
  diamond: 'M6,1 L11,6 L6,11 L1,6 Z',
  cross: 'M2,2 L10,10 M10,2 L2,10',
};

export const Swatch: React.FC<{ shape: PointShape; color: keyof typeof MAP_COLORS }> = ({
  shape,
  color,
}) => {
  const outline = shape === 'ring' || shape === 'cross';
  return (
    <svg width={12} height={12} aria-hidden="true" className="shrink-0">
      <path
        d={SWATCH_PATHS[shape]}
        fill={outline ? 'none' : MAP_COLORS[color]}
        stroke={outline ? MAP_COLORS[color] : 'none'}
        strokeWidth={1.5}
      />
    </svg>
  );
};

/** What each shape and colour means under the current lens, with its count. */
const MapLegend: React.FC<{ entries: readonly LegendEntry[] }> = ({ entries }) => {
  const { t } = useTranslation('polity');
  return (
    <ul data-testid="polity-map-legend" className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
      {entries.map((entry) => (
        <li
          key={entry.key}
          data-testid={`polity-legend-${entry.key}`}
          className="flex items-center gap-1.5"
        >
          <Swatch shape={entry.shape} color={entry.color} />
          <span>{legendLabel(t, entry.key)}</span>
          <span className="tabular-nums text-muted-foreground">{entry.count}</span>
        </li>
      ))}
    </ul>
  );
};

export default MapLegend;
