/**
 * BallotComplexityPanel — simulates how ballot design complexity
 * causes spoiled (null) ballots and which voting methods lose the most votes.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface MethodResult {
  method: string;
  null_rate: number;
  blank_rate: number;
  effective_voters: number;
  winner: string | null;
  winner_changed: boolean;
}

interface CurvePt {
  n_candidates: number;
  null_rate_by_method: Record<string, number>;
}

interface ComplexityData {
  results: MethodResult[];
  candidate_count_curve: CurvePt[];
  most_inclusive_method: string;
  least_inclusive_method: string;
  pedagogical_note: string;
}

// ── Ballot design config ──────────────────────────────────────────────────────

const BALLOT_TYPES: {
  method: string;
  labelKey: string;
  visual: string;
  stars: number;
}[] = [
  { method: 'plurality', labelKey: 'ballot.typePlurality', visual: '○ A  ○ B  ○ C', stars: 1 },
  { method: 'approval', labelKey: 'ballot.typeApproval', visual: '☐ A  ☐ B  ☐ C', stars: 2 },
  { method: 'irv', labelKey: 'ballot.typeIRV', visual: '1_ A  2_ B  3_ C', stars: 3 },
  { method: 'borda', labelKey: 'ballot.typeBorda', visual: 'A:2  B:1  C:0', stars: 3 },
  {
    method: 'star_voting',
    labelKey: 'ballot.typeSTAR',
    visual: 'A ★★★☆☆  B ★★☆☆☆  C ★★★★☆',
    stars: 3,
  },
  {
    method: 'majority_judgment',
    labelKey: 'ballot.typeMJ',
    visual: 'A [TB]  B [AB]  C [P]',
    stars: 2,
  },
  { method: 'schulze', labelKey: 'ballot.typeSchulze', visual: 'A>B>C  (matrice)', stars: 4 },
];

// ── Colour helpers ────────────────────────────────────────────────────────────

const LINE_COLORS = [
  '#005CAB',
  '#C8590A',
  '#007A33',
  '#9b59b6',
  '#e67e22',
  '#17a2b8',
  '#e83e8c',
  '#6c757d',
];
function lineColor(i: number): string {
  return LINE_COLORS[i % LINE_COLORS.length];
}

function barColor(nullRate: number): string {
  if (nullRate < 0.02) return '#198754';
  if (nullRate < 0.05) return '#fd7e14';
  return '#dc3545';
}

function starsElement(n: number): string {
  return '★'.repeat(n) + '☆'.repeat(Math.max(0, 4 - n));
}

// ── Main panel ────────────────────────────────────────────────────────────────

const BallotComplexityPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [eduLevel, setEduLevel] = useState(0.7);
  const [ftvPct, setFtvPct] = useState(0.1);
  const sim = $api.useMutation('post', '/api/v2/election/ballot-complexity');
  const data: ComplexityData | null = (sim.data as ComplexityData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('ballot.error') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (edu: number, ftv: number) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          education_level: edu,
          first_time_voter_pct: ftv,
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(eduLevel, ftvPct);

  const schedule = useCallback(
    (edu: number, ftv: number) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => runSimulation(edu, ftv), DEBOUNCE_MS);
    },
    [runSimulation]
  );

  // Auto-recalculate when sliders change after first run
  const hasData = data !== null;
  useEffect(() => {
    if (!hasData) return;
    schedule(eduLevel, ftvPct);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eduLevel, ftvPct]);

  // ── Bar chart data ──────────────────────────────────────────────────────
  const barData =
    data?.results.map((r) => ({
      method: r.method,
      null_rate: Math.round(r.null_rate * 1000) / 10, // as %
      fill: barColor(r.null_rate),
    })) ?? [];

  // ── Curve data ──────────────────────────────────────────────────────────
  const curveData =
    data?.candidate_count_curve.map((pt) => ({
      n: pt.n_candidates,
      ...Object.fromEntries(
        Object.entries(pt.null_rate_by_method).map(([m, v]) => [m, Math.round(v * 1000) / 10])
      ),
    })) ?? [];

  const methodKeys = data?.results.map((r) => r.method) ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('ballot.educationLevel')}: <strong>{eduLevel.toFixed(2)}</strong>
          </label>
          <Range
            data-testid="education-slider"
            min={0}
            max={1}
            step={0.05}
            value={eduLevel}
            onChange={(e) => setEduLevel(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('ballot.firstTimeVoter')}: <strong>{Math.round(ftvPct * 100)}%</strong>
          </label>
          <Range
            data-testid="ftv-slider"
            min={0}
            max={0.5}
            step={0.02}
            value={ftvPct}
            onChange={(e) => setFtvPct(Number(e.target.value))}
          />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}>
            {loading ? <Spinner size="sm" /> : t('ballot.run')}
          </Button>
        </Col>
        {data &&
          data.results.length > 0 &&
          (() => {
            // ballot data already has winner-per-method! Build the map
            const winnersByMethod: Record<string, string | null> = {};
            data.results.forEach((r) => {
              winnersByMethod[r.method] = r.winner;
            });
            const changedCount = data.results.filter((r) => r.winner_changed).length;
            return (
              <Col xs="auto">
                <PinToCentralButton
                  type="ballot"
                  icon="📋"
                  label={t('ballot.run')}
                  summary={
                    changedCount > 0
                      ? `${changedCount}/${data.results.length} ${t('lab.methodsChanged')}`
                      : t('lab.winnerStable')
                  }
                  methodsChanged={changedCount}
                  winnersByMethod={winnersByMethod}
                />
              </Col>
            );
          })()}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('ballot.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="success" data-testid="most-inclusive-badge">
              {t('ballot.mostInclusive')}: {data.most_inclusive_method}
            </Badge>
            <Badge variant="danger" data-testid="least-inclusive-badge">
              {t('ballot.leastInclusive')}: {data.least_inclusive_method}
            </Badge>
            {data.results.some((r) => r.winner_changed) && (
              <Badge variant="warning" data-testid="winner-changed-badge">
                {t('ballot.winnerChangedAlert')}
              </Badge>
            )}
          </div>

          {/* Horizontal bar chart — null rate per method */}
          <div className="mb-4" data-testid="null-rate-bar-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('ballot.barTitle')}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={barData}
                layout="vertical"
                margin={{ top: 4, right: 32, bottom: 4, left: 70 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" unit="%" domain={[0, 'auto']} tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="method" tick={{ fontSize: 10 }} width={68} />
                <Tooltip formatter={(v: number) => `${v}%`} />
                <Bar dataKey="null_rate" name={t('ballot.nullRate')} radius={[0, 3, 3, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="flex gap-3 mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
              <span style={{ color: '#198754' }}>■ &lt;2% {t('ballot.low')}</span>
              <span style={{ color: '#fd7e14' }}>■ 2-5% {t('ballot.medium')}</span>
              <span style={{ color: '#dc3545' }}>■ &gt;5% {t('ballot.high')}</span>
            </div>
          </div>

          {/* Curve: n_candidates vs null_rate */}
          <div className="mb-4" data-testid="candidate-curve-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('ballot.curveTitle')}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={curveData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="n"
                  label={{
                    value: t('ballot.nCandidates'),
                    position: 'insideBottom',
                    offset: -2,
                    fontSize: 10,
                  }}
                />
                <YAxis unit="%" tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {methodKeys.map((m, i) => (
                  <Line
                    key={m}
                    type="monotone"
                    dataKey={m}
                    stroke={lineColor(i)}
                    dot={false}
                    strokeWidth={1.5}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Results table */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('ballot.tableTitle')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50 mb-4"
            data-testid="results-table"
          >
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('ballot.method')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('ballot.nullRate')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('ballot.effectiveVoters')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('ballot.winner')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('ballot.changed')}</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr key={r.method} data-testid={`result-row-${r.method}`}>
                  <td style={{ fontSize: '0.78rem' }}>
                    <code>{r.method}</code>
                  </td>
                  <td style={{ fontSize: '0.78rem', color: barColor(r.null_rate) }}>
                    {Math.round(r.null_rate * 100)}%
                  </td>
                  <td style={{ fontSize: '0.78rem' }}>{r.effective_voters}</td>
                  <td style={{ fontSize: '0.78rem' }}>{r.winner ?? '—'}</td>
                  <td style={{ fontSize: '0.78rem' }}>
                    {r.winner_changed ? (
                      <span style={{ color: '#dc3545' }}>⚠</span>
                    ) : (
                      <span style={{ color: '#198754' }}>✓</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          {/* Ballot design section */}
          <div className="font-semibold mb-2" style={{ fontSize: '0.85rem' }}>
            {t('ballot.designTitle')}
          </div>
          <div className="flex flex-wrap gap-2 mb-3" data-testid="ballot-design-section">
            {BALLOT_TYPES.filter((bt) => methodKeys.includes(bt.method)).map((bt) => {
              const result = data.results.find((r) => r.method === bt.method);
              return (
                <div
                  key={bt.method}
                  className="border border-border rounded p-2"
                  style={{ fontSize: '0.72rem', background: '#f8f9fa', minWidth: 120 }}
                >
                  <div className="font-semibold">{bt.method}</div>
                  <code style={{ fontSize: '0.65rem', color: '#6c757d' }}>{bt.visual}</code>
                  <div className="mt-1" style={{ color: '#6c757d' }}>
                    {starsElement(bt.stars)}
                  </div>
                  {result && (
                    <div style={{ color: barColor(result.null_rate), fontWeight: 600 }}>
                      {Math.round(result.null_rate * 100)}% nuls
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('ballot.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default BallotComplexityPanel;
