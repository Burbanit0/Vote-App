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
  electionRows,
  hasStanding,
  pressureRows,
  standingRows,
  type ElectionRow,
} from '../../lib/polity/macroSeries';
import { MAP_COLORS } from '../../lib/polity/mapScene';
import { usePolityCtx } from './PolityController';

// The run's curves (Recharts, loaded on demand — ADR-005): the sitting
// president's standing, the pressure citizens put on them, and each
// presidential election's turnout and blank share with where that share comes
// from. A marker follows the player; a click on a chart moves it.

const PRESSURE_COLORS: Record<(typeof PRESSURE_KEYS)[number], string> = {
  nothing: MAP_COLORS.muted,
  signPetition: MAP_COLORS.sky,
  launchPetition: MAP_COLORS.blue,
  mobilize: MAP_COLORS.vermillion,
  waitForElection: MAP_COLORS.green,
};
const PRESSURE_LABELS: Record<(typeof PRESSURE_KEYS)[number], string> = {
  nothing: 'map.legend.nothing',
  signPetition: 'map.legend.signPetition',
  launchPetition: 'map.legend.launchPetition',
  mobilize: 'map.legend.mobilize',
  waitForElection: 'map.legend.waitForElection',
};
const OUTCOME_KEYS: Record<ElectionRow['outcome'], string> = {
  elected: 'macro.outcomeElected',
  no_winner: 'macro.outcomeNoWinner',
  invalidated: 'macro.outcomeInvalidated',
};
const SOURCE_KEYS: Record<NonNullable<ElectionRow['blankSource']>, string> = {
  invalidation_check: 'macro.sourceInvalidationCheck',
  ballots: 'macro.sourceBallots',
  audit_sample: 'macro.sourceAuditSample',
};

const percent = (value: number | null) => (value === null ? null : `${Math.round(value * 100)} %`);

const MacroCurvesPanel: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, tick, setTick } = usePolityCtx();
  const theme = useChartTheme();
  if (!overview) return null;

  const standings = standingRows(overview.standings);
  const pressure = pressureRows(overview.standings);
  const elections = electionRows(overview.elections);
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
              <Line
                dataKey="legitimacy"
                name={t('macro.legitimacy')}
                stroke={MAP_COLORS.blue}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                dataKey="mandateStrength"
                name={t('macro.mandateStrength')}
                stroke={MAP_COLORS.green}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                dataKey="ecart"
                name={t('macro.ecart')}
                stroke={MAP_COLORS.vermillion}
                strokeDasharray="4 2"
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
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
                name={t(PRESSURE_LABELS[key])}
                fill={PRESSURE_COLORS[key]}
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
                <th scope="col" className="px-2 py-1">
                  {t('macro.tableTick')}
                </th>
                <th scope="col" className="px-2 py-1">
                  {t('macro.tableOutcome')}
                </th>
                <th scope="col" className="px-2 py-1">
                  {t('macro.tableWinner')}
                </th>
                <th scope="col" className="px-2 py-1">
                  {t('macro.turnout')}
                </th>
                <th scope="col" className="px-2 py-1">
                  {t('macro.blankShare')}
                </th>
                <th scope="col" className="px-2 py-1">
                  {t('macro.tableSource')}
                </th>
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
                  <td className="px-2 py-0.5 tabular-nums">{e.winner ?? '—'}</td>
                  <td className="px-2 py-0.5 tabular-nums">
                    {percent(e.turnout) ?? t('macro.unavailable')}
                  </td>
                  <td className="px-2 py-0.5 tabular-nums">
                    {percent(e.blankShare) ?? t('macro.unavailable')}
                  </td>
                  <td className="px-2 py-0.5">
                    {e.blankSource ? t(SOURCE_KEYS[e.blankSource]) : t('macro.unavailable')}
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
