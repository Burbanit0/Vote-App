import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from './PlaygroundController';
import { RULE_LABELS, type Rule } from '../../lib/playgroundVoting';
import { LEADER_RULES } from '../../lib/scorecard';
import { selectCls } from './playgroundFields';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// NonSpatialProfileMap — the read-only biplot for statistical-culture profiles
// (Impartial, Mallows, urn, Plackett-Luce, DiDi, stratification). These have no
// candidate geometry, so the backend places voters AND candidates in one plane via
// PCA + utility-weighted centroids. The map is observational: you read the emergent
// structure and the winner, but candidates aren't draggable (their position is a
// consequence of the ballots, not a choice).

// Client rule id → backend method slug (only the compared LEADER_RULES differ).
const BACKEND_SLUG: Partial<Record<Rule, string>> = {
  condorcet: 'copeland',
  star: 'star_voting',
  score: 'simple_score',
};
const slugOf = (r: Rule): string => BACKEND_SLUG[r] ?? r;

const SVG = 320;
const PAD = 26;
// Display points live in ~[-1,1]; project to the padded SVG box.
const toSvg = (v: number): number => PAD + ((v + 1) / 2) * (SVG - 2 * PAD);

const candColor = (i: number): string => CANDIDATE_COLORS_LIGHT[i % CANDIDATE_COLORS_LIGHT.length];

const NonSpatialProfileMap: React.FC = () => {
  const { t } = useTranslation('playground');
  const { result, loading, leaderRule, setLeaderRule } = usePlaygroundCtx();

  if (!result || loading) {
    return (
      <div
        data-testid="nonspatial-map"
        className="flex h-64 items-center justify-center rounded-md border border-dashed border-border text-xs text-muted-foreground"
      >
        {t('nonspatial.computing')}
      </div>
    );
  }

  const { display_points, candidate_points, candidate_names } = result;
  const winnerName = result.methods[slugOf(leaderRule)]?.winner ?? null;
  const winnerIdx = winnerName ? candidate_names.indexOf(winnerName) : -1;
  // Cap voter dots for perf; the cloud shape reads the same.
  const voterPts = display_points.slice(0, 400);

  return (
    <div data-testid="nonspatial-map" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <select
          aria-label={t('method.ruleLabel')}
          className={selectCls}
          value={leaderRule}
          onChange={(e) => setLeaderRule(e.target.value as Rule)}
        >
          {LEADER_RULES.map((r) => (
            <option key={r} value={r}>
              {RULE_LABELS[r]}
            </option>
          ))}
        </select>
      </div>

      <svg
        viewBox={`0 0 ${SVG} ${SVG}`}
        className="mx-auto block w-full rounded-md border border-border bg-card"
        style={{ maxWidth: 460, maxHeight: '52vh' }}
        role="img"
        aria-label={t('nonspatial.aria')}
      >
        {/* voter cloud */}
        {voterPts.map((p, i) => (
          <circle
            key={i}
            cx={toSvg(p[0])}
            cy={toSvg(-p[1])}
            r={1.8}
            className="fill-muted-foreground/40"
          />
        ))}
        {/* candidates (biplot centroids) */}
        {(candidate_points ?? []).map((p, i) => {
          const isWin = i === winnerIdx;
          return (
            <g key={i}>
              {isWin && (
                <circle
                  cx={toSvg(p[0])}
                  cy={toSvg(-p[1])}
                  r={11}
                  fill="none"
                  stroke={candColor(i)}
                  strokeWidth={2}
                  opacity={0.6}
                />
              )}
              <circle
                cx={toSvg(p[0])}
                cy={toSvg(-p[1])}
                r={6}
                fill={candColor(i)}
                stroke="white"
                strokeWidth={1.5}
              />
              <text
                x={toSvg(p[0])}
                y={toSvg(-p[1]) - 10}
                textAnchor="middle"
                className="fill-foreground text-[10px] font-medium"
              >
                {candidate_names[i]}
              </text>
            </g>
          );
        })}
      </svg>

      <p className="text-sm">
        {winnerName ? (
          <>
            {t('nonspatial.winnerPre')}{' '}
            <strong style={{ color: candColor(winnerIdx) }}>{winnerName}</strong>
          </>
        ) : (
          t('nonspatial.noWinner')
        )}
      </p>
      <p className="text-[0.7rem] text-muted-foreground">{t('nonspatial.caption')}</p>
    </div>
  );
};

export default NonSpatialProfileMap;
