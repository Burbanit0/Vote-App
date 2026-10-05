import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useChartTheme } from '../../hooks/useChartTheme';
import {
  PRESSURE_KEYS,
  clickedTick,
  hasStanding,
  pressureRows,
  type ElectionInput,
} from '../../lib/polity/macroSeries';
import { mapColors, type MapColor } from '../../lib/polity/mapScene';
import { usePolityCtx } from './PolityController';

// The run's curves (Recharts, loaded on demand — ADR-005): the sitting
// president's standing, the pressure citizens put on them, and each
// presidential election's turnout and blank share with where that share comes
// from. A marker follows the player; a click on a chart moves it.

// Colours by name, resolved against the theme's palette at render -- the act a curve shows is the
// same act the map's lens shows, so both must take the same step in dark mode.
const PRESSURE_COLORS: Record<(typeof PRESSURE_KEYS)[number], MapColor> = {
  nothing: 'muted',
  signPetition: 'sky',
  launchPetition: 'blue',
  mobilize: 'vermillion',
  waitForElection: 'green',
};
// The standing's four lines, by the API's field: label, colour, dash.
const STANDING_LINES = [
  ['legitimacy', 'macro.legitimacy', 'blue', undefined],
  ['mandate_strength', 'macro.mandateStrength', 'green', undefined],
  ['approval', 'macro.approval', 'purple', undefined],
  ['ecart', 'macro.ecart', 'vermillion', '4 2'],
] as const;
const ELECTION_COLUMNS = [
  'tableTick',
  'tableOutcome',
  'tableWinner',
  'turnout',
  'blankShare',
  'tableSource',
] as const;
const OUTCOME_KEYS: Record<ElectionInput['outcome'], string> = {
  elected: 'macro.outcomeElected',
  no_winner: 'macro.outcomeNoWinner',
  invalidated: 'macro.outcomeInvalidated',
};
const SOURCE_KEYS: Record<NonNullable<ElectionInput['blank_source']>, string> = {
  invalidation_check: 'macro.sourceInvalidationCheck',
  ballots: 'macro.sourceBallots',
  audit_sample: 'macro.sourceAuditSample',
};

const percent = (value: number | null | undefined) =>
  value == null ? null : `${Math.round(value * 100)} %`;

const MacroCurvesPanel: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, tick, setTick, setCitizen } = usePolityCtx();
  const theme = useChartTheme();
  const colors = mapColors(theme.isDark);
  if (!overview) return null;

  const { standings, elections } = overview;
  const pressure = pressureRows(standings);
  const jump = (state: { activeLabel?: string | number } | null) => {
    const target = clickedTick(state);
    if (target !== null) setTick(target);
  };
  const axis = { stroke: theme.tickFill, fontSize: 11 };
  const marker = <ReferenceLine x={tick} stroke={theme.refStroke} strokeWidth={2} />;

  return (
    <div data-testid="polity-macro-panel" className="flex flex-col gap-4 px-3 py-2">
      <p className="text-xs text-muted-foreground">{t('macro.clickHint')}</p>

      <figure data-testid="polity-macro-standing">
        <figcaption className="mb-1 text-sm font-semibold">{t('macro.standingTitle')}</figcaption>
        {hasStanding(standings) ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={standings} onClick={jump}>
              <CartesianGrid stroke={theme.gridStroke} strokeDasharray="3 3" />
              <XAxis dataKey="tick" {...axis} />
              <YAxis domain={[0, 1]} {...axis} />
              <Tooltip contentStyle={theme.tooltipStyle} />
              <Legend />
              {STANDING_LINES.map(([field, label, color, dash]) => (
                <Line
                  key={field}
                  dataKey={field}
                  name={t(label)}
                  stroke={colors[color]}
                  strokeDasharray={dash}
                  dot={false}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              ))}
              {marker}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-xs text-muted-foreground">{t('macro.noStanding')}</p>
        )}
      </figure>

      <figure data-testid="polity-macro-pressure">
        <figcaption className="mb-1 text-sm font-semibold">{t('macro.pressureTitle')}</figcaption>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={pressure} onClick={jump}>
            <CartesianGrid stroke={theme.gridStroke} strokeDasharray="3 3" />
            <XAxis dataKey="tick" {...axis} />
            <YAxis allowDecimals={false} {...axis} />
            <Tooltip contentStyle={theme.tooltipStyle} />
            <Legend />
            {PRESSURE_KEYS.map((key) => (
              <Bar
                key={key}
                dataKey={key}
                stackId="acts"
                name={t(`map.legend.${key}`)}
                fill={colors[PRESSURE_COLORS[key]]}
                isAnimationActive={false}
              />
            ))}
            {marker}
          </BarChart>
        </ResponsiveContainer>
      </figure>

      <figure data-testid="polity-macro-elections">
        <figcaption className="mb-1 text-sm font-semibold">{t('macro.electionsTitle')}</figcaption>
        {elections.length === 0 ? (
          <p className="text-xs text-muted-foreground">{t('macro.noElections')}</p>
        ) : (
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-border">
                {ELECTION_COLUMNS.map((column) => (
                  <th key={column} scope="col" className="px-2 py-1">
                    {t(`macro.${column}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {elections.map((e) => (
                <tr
                  key={`${e.tick}-${e.outcome}`}
                  data-testid={`polity-election-${e.tick}`}
                  className="border-b border-border/50"
                >
                  <td className="px-2 py-0.5">
                    <button
                      type="button"
                      className="underline-offset-2 hover:underline"
                      onClick={() => setTick(e.tick)}
                    >
                      {e.tick}
                    </button>
                  </td>
                  <td className="px-2 py-0.5">{t(OUTCOME_KEYS[e.outcome])}</td>
                  <td className="px-2 py-0.5 tabular-nums">
                    {e.winner == null ? (
                      '—'
                    ) : (
                      // The winner's story opens beside the map.
                      <button
                        type="button"
                        className="underline-offset-2 hover:underline"
                        aria-label={t('map.select', { id: e.winner })}
                        onClick={() => setCitizen(e.winner ?? null)}
                      >
                        {e.winner}
                      </button>
                    )}
                  </td>
                  <td className="px-2 py-0.5 tabular-nums">
                    {percent(e.turnout) ?? t('macro.unavailable')}
                  </td>
                  <td className="px-2 py-0.5 tabular-nums">
                    {percent(e.blank_share) ?? t('macro.unavailable')}
                  </td>
                  <td className="px-2 py-0.5">
                    {e.blank_source ? t(SOURCE_KEYS[e.blank_source]) : t('macro.unavailable')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </figure>
    </div>
  );
};

export default MacroCurvesPanel;
