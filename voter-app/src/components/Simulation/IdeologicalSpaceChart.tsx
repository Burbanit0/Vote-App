import React, { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { useTranslation } from 'react-i18next';
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

// ── Constants ──────────────────────────────────────────────────────────────

const CULTURAL_ISSUES = ['gender_equality', 'immigration', 'crime_safety', 'defense'];
const ECONOMIC_ISSUES = ['economy', 'taxes', 'minimum_wage', 'business_regulation'];

const VOTER_SINCERE = '#4e79a7';
const VOTER_STRATEGIC = '#f28e2b';

const CANDIDATE_PALETTE = [
  '#e15759',
  '#59a14f',
  '#76b7b2',
  '#edc948',
  '#b07aa1',
  '#ff9da7',
  '#86bcb6',
  '#4e79a7',
];

const getMethodLabel = (t: (key: string) => string, method: string): string => {
  const key = `methods.${method}.label`;
  const label = t(key);
  return label !== key ? label : method;
};

// ── Types (inline — no extra files needed) ─────────────────────────────────

interface VoterPoint {
  id: number;
  political_lean_normalized: number;
  voting_style: string;
  issue_positions: Record<string, number>;
}

interface CandidatePoint {
  id: number;
  name: string;
  party: string;
  ideology_position: number;
  policies: Record<string, number>;
}

interface Props {
  voters: VoterPoint[];
  candidates: CandidatePoint[];
  winnersByMethod?: Record<string, string>;
  selectedMethod?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function avgIssues(positions: Record<string, number>, keys: string[]): number {
  const vals = keys.map((k) => positions[k]).filter((v) => v !== undefined);
  return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0.5;
}

// Y axis = avg(cultural issues) − avg(economic issues).
// Positive → more culturally conservative than economically.
// Negative → more economically conservative than culturally.
function computeY(positions: Record<string, number>): number {
  return avgIssues(positions, CULTURAL_ISSUES) - avgIssues(positions, ECONOMIC_ISSUES);
}

// ── Custom tooltip ─────────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  if ('voting_style' in d) {
    return (
      <div
        style={{
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 12,
          boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
        }}
      >
        <div>
          <strong>Voter #{d.id}</strong>
        </div>
        <div>Style: {d.voting_style}</div>
        <div>
          X: {d.x.toFixed(2)} &nbsp; Y: {d.y.toFixed(2)}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'white',
        border: '1px solid #ddd',
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: 12,
        boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
      }}
    >
      <div>
        <strong>{d.name}</strong>
      </div>
      <div>{d.party}</div>
      <div>
        Position: {d.x.toFixed(2)} &nbsp; Y: {d.y.toFixed(2)}
      </div>
    </div>
  );
};

// ── Component ──────────────────────────────────────────────────────────────

const IdeologicalSpaceChart: React.FC<Props> = ({
  voters,
  candidates,
  winnersByMethod,
  selectedMethod: initialMethod,
}) => {
  const { t } = useTranslation();
  const [activeMethod, setActiveMethod] = useState<string | undefined>(
    () => initialMethod ?? (winnersByMethod ? Object.keys(winnersByMethod)[0] : undefined)
  );

  const candidateColorMap = useMemo(
    () =>
      Object.fromEntries(
        candidates.map((c, i) => [c.name, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
      ),
    [candidates]
  );

  const currentWinner = activeMethod ? winnersByMethod?.[activeMethod] : undefined;

  const voterData = useMemo(
    () =>
      voters.map((v) => ({
        x: v.political_lean_normalized,
        y: computeY(v.issue_positions),
        voting_style: v.voting_style,
        id: v.id,
      })),
    [voters]
  );

  const candidateData = useMemo(
    () =>
      candidates.map((c) => ({
        x: c.ideology_position,
        y: computeY(c.policies),
        name: c.name,
        party: c.party,
      })),
    [candidates]
  );

  // ── Custom shapes (defined inside component to close over candidateColorMap
  //    and currentWinner without extra prop drilling) ───────────────────────

  const VoterShape = (props: any) => {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null) return null;
    return (
      <circle
        cx={cx}
        cy={cy}
        r={3}
        fill={payload.voting_style === 'sincere' ? VOTER_SINCERE : VOTER_STRATEGIC}
        opacity={0.3}
      />
    );
  };

  const CandidateShape = (props: any) => {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null) return null;
    const color = candidateColorMap[payload.name] ?? '#999';
    const isWinner = currentWinner === payload.name;

    return (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={14}
          fill={color}
          stroke={isWinner ? '#111' : 'white'}
          strokeWidth={isWinner ? 3 : 1.5}
          opacity={0.9}
        />
        {isWinner && (
          <text x={cx} y={cy + 5} textAnchor="middle" fontSize={14} fill="white" fontWeight="bold">
            ★
          </text>
        )}
        <text
          x={cx}
          y={cy + 28}
          textAnchor="middle"
          fontSize={11}
          fill="#333"
          fontWeight={isWinner ? '700' : '500'}
        >
          {payload.name}
        </text>
      </g>
    );
  };

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <Card>
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
        <strong>{t('simulation.ideologicalSpace.title')}</strong>
        {winnersByMethod && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Object.entries(winnersByMethod).map(([method, winner]) => (
              <Button
                key={method}
                size="sm"
                variant={activeMethod === method ? 'primary' : 'outline-secondary'}
                onClick={() => setActiveMethod(method)}
              >
                {getMethodLabel(t, method)}
                {winner && (
                  <span
                    className="ms-1 badge"
                    style={{
                      backgroundColor: candidateColorMap[winner] ?? '#999',
                      color: 'white',
                      fontSize: '0.75em',
                    }}
                  >
                    {winner}
                  </span>
                )}
              </Button>
            ))}
          </div>
        )}
      </CardHeader>

      <CardBody>
        {/* Voter colour legend */}
        <div className="flex gap-4 mb-3 flex-wrap items-center">
          <span className="font-semibold text-sm text-muted-foreground">
            {t('simulation.ideologicalSpace.voters')}
          </span>
          {[
            { label: t('simulation.ideologicalSpace.sincere'), color: VOTER_SINCERE },
            { label: t('simulation.ideologicalSpace.strategic'), color: VOTER_STRATEGIC },
          ].map(({ label, color }) => (
            <span key={label} className="flex items-center gap-1">
              <svg width={12} height={12}>
                <circle cx={6} cy={6} r={5} fill={color} opacity={0.7} />
              </svg>
              <small>{label}</small>
            </span>
          ))}

          <span className="font-semibold text-sm text-muted-foreground ms-3">
            {t('simulation.ideologicalSpace.candidates')}
          </span>
          {candidates.map((c) => (
            <span key={c.name} className="flex items-center gap-1">
              <svg width={12} height={12}>
                <circle cx={6} cy={6} r={5} fill={candidateColorMap[c.name] ?? '#999'} />
              </svg>
              <small>
                {c.name}
                {currentWinner === c.name && (
                  <span className="ms-1" style={{ color: '#f0a500' }}>
                    ★
                  </span>
                )}
              </small>
            </span>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={450}>
          <ScatterChart margin={{ top: 20, right: 30, bottom: 50, left: 50 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />

            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 1]}
              tickCount={6}
              tick={{ fontSize: 10 }}
              label={{
                value: t('simulation.ideologicalSpace.xAxis'),
                position: 'insideBottom',
                offset: -20,
                fontSize: 11,
                fill: '#555',
              }}
            />

            <YAxis
              type="number"
              dataKey="y"
              domain={[-1, 1]}
              tickCount={5}
              tick={{ fontSize: 10 }}
              label={{
                value: t('simulation.ideologicalSpace.yAxis'),
                angle: -90,
                position: 'insideLeft',
                offset: 15,
                fontSize: 11,
                fill: '#555',
              }}
            />

            {/* Fixed nominal size — actual sizing is handled by custom shapes */}
            <ZAxis range={[25, 25]} />

            <Tooltip content={<CustomTooltip />} />

            {/* Quadrant reference lines */}
            <ReferenceLine x={0.5} stroke="#bbb" strokeDasharray="4 2" />
            <ReferenceLine y={0} stroke="#bbb" strokeDasharray="4 2" />

            <Scatter data={voterData} shape={<VoterShape />} isAnimationActive={false} />
            <Scatter data={candidateData} shape={<CandidateShape />} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>

        <p className="text-muted-foreground text-sm mt-1 mb-0">
          {t('simulation.ideologicalSpace.description')}
          {winnersByMethod && activeMethod && (
            <>
              {' '}
              {t('simulation.ideologicalSpace.winnerDescription')}{' '}
              <strong>{getMethodLabel(t, activeMethod)}</strong>.
            </>
          )}
        </p>
      </CardBody>
    </Card>
  );
};

export default IdeologicalSpaceChart;
