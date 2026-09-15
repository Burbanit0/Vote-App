import React from 'react';
import { useTranslation } from 'react-i18next';
import type { Scene } from '../../lib/polity/mapScene';
import { legendLabel, Swatch } from './MapLegend';
import { usePolityCtx } from './PolityController';

/** The map's reading as a table, one row per citizen: the same information without the canvas. */
const PopulationTable: React.FC<{ scene: Scene }> = ({ scene }) => {
  const { t } = useTranslation('polity');
  const { overview, citizen, setCitizen } = usePolityCtx();
  return (
    <details data-testid="polity-table" className="mt-2 text-xs">
      <summary className="cursor-pointer text-muted-foreground">{t('map.table')}</summary>
      <div className="max-h-72 overflow-auto">
        <table className="mt-1 w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border">
              <th scope="col" className="px-2 py-1">
                {t('map.tableCitizen')}
              </th>
              <th scope="col" className="px-2 py-1">
                {t('map.tableParty')}
              </th>
              <th scope="col" className="px-2 py-1">
                {t('map.tableReading')}
              </th>
            </tr>
          </thead>
          <tbody>
            {scene.points.map((point) => (
              <tr
                key={point.id}
                data-testid={`polity-row-${point.id}`}
                aria-selected={citizen === point.id}
                className={citizen === point.id ? 'bg-primary/10' : undefined}
              >
                <td className="px-2 py-0.5">
                  <button
                    type="button"
                    className="underline-offset-2 hover:underline"
                    aria-label={t('map.select', { id: point.id })}
                    onClick={() => setCitizen(point.id)}
                  >
                    {point.id}
                  </button>
                </td>
                <td className="px-2 py-0.5 tabular-nums">
                  {overview?.citizen_parties[point.id] ?? '—'}
                </td>
                <td className="px-2 py-0.5">
                  <span className="flex items-center gap-1.5">
                    <Swatch shape={point.shape} color={point.color} />
                    {legendLabel(t, point.legend)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
};

export default PopulationTable;
