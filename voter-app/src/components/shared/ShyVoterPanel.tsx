/**
 * ShyVoterPanel — simulates the Bradley / Shy Tory effect:
 * voters declare a socially acceptable preference in polls but vote sincerely.
 */
import React, { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { $api } from '../../api/hooks';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface ShyData {
  real_winner: string;
  poll_winner: string;
  polls_wrong: boolean;
  shy_candidate: string;
  poll_results: {
    poll_n: number;
    predicted: Record<string, number>;
    real: Record<string, number>;
  }[];
  systematic_error: Record<string, number>;
  real_results: Record<string, number>;
  avg_poll_results: Record<string, number>;
  social_desirability_curve: { factor: number; poll_error: number; winner_wrong_pct: number }[];
  pedagogical_note: string;
}

// ── Historical examples ───────────────────────────────────────────────────────

const HISTORICAL = [
  {
    year: '1982',
    country: '🇺🇸',
    event: 'Bradley Effect',
    detail: 'Tom Bradley leading polls by 22%, lost by 1.5%',
  },
  {
    year: '1992',
    country: '🇬🇧',
    event: 'Shy Tory',
    detail: 'Conservateurs sous-estimés de 8 pts — victoire surprise Major',
  },
  {
    year: '2016',
    country: '🇬🇧',
    event: 'Brexit',
    detail: 'Leave sous-estimé de 4 pts dans les derniers sondages',
  },
  {
    year: '2002–',
    country: '🇫🇷',
    event: 'Phénomène Le Pen',
    detail: 'RN systématiquement sous-estimé de 2-5 pts',
  },
];

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22', '#e83e8c'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Main panel ────────────────────────────────────────────────────────────────

const ShyVoterPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const candidateNames = config.candidates.map((c) => c.name);

  const [sdFactor, setSdFactor] = useState(0.4);
  const [shyIdx, setShyIdx] = useState(0);
  const sim = $api.useMutation('post', '/api/v2/election/shy-voter');
  const data: ShyData | null = (sim.data as ShyData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('shyVoter.apiError') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (factor: number, idx: number) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          shy_candidate_idx: idx,
          social_desirability_factor: factor,
          num_polls: 10,
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(sdFactor, shyIdx);

  const handleFactorChange = (v: number) => {
    setSdFactor(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(v, shyIdx), DEBOUNCE_MS);
  };

  // ── Grouped bar chart data (avg poll vs real) ───────────────────────────
  const barData = data
    ? candidateNames.map((c) => ({
        name: c,
        poll: Math.round((data.avg_poll_results[c] ?? 0) * 100),
        real: Math.round((data.real_results[c] ?? 0) * 100),
      }))
    : [];

  // ── Timeline data: polls + real as last point ───────────────────────────
  const timelineData = data
    ? [
        ...data.poll_results.map((pr) => ({
          x: pr.poll_n,
          type: 'poll' as const,
          ...Object.fromEntries(
            candidateNames.map((c) => [c, Math.round((pr.predicted[c] ?? 0) * 100)])
          ),
        })),
        {
          x: data.poll_results.length + 1,
          type: 'real' as const,
          ...Object.fromEntries(
            candidateNames.map((c) => [c, Math.round((data.real_results[c] ?? 0) * 100)])
          ),
        },
      ]
    : [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('shyVoter.factorSlider')}: <strong>{sdFactor.toFixed(2)}</strong>
          </label>
          <Range
            data-testid="sdf-slider"
            min={0}
            max={1}
            step={0.05}
            value={sdFactor}
            onChange={(e) => handleFactorChange(Number(e.target.value))}
          />
          <div className="flex justify-between" style={{ fontSize: '0.68rem', color: '#6c757d' }}>
            <span>0 — {t('shyVoter.factorLow')}</span>
            <span>0.3 — Brexit</span>
            <span>0.7+ — {t('shyVoter.factorHigh')}</span>
          </div>
        </Col>
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">{t('shyVoter.candidateSelect')}</label>
          <Select
            size="sm"
            value={shyIdx}
            data-testid="shy-candidate-select"
            onChange={(e) => setShyIdx(Number(e.target.value))}
          >
            {candidateNames.map((name, i) => (
              <option key={i} value={i}>
                {name}
              </option>
            ))}
          </Select>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}>
            {loading ? <Spinner size="sm" /> : t('shyVoter.run')}
          </Button>
        </Col>
        {data && (
          <Col xs="auto">
            <PinToCentralButton
              type="shyvoter"
              icon="🤫"
              label={t('shyVoter.run')}
              summary={
                data.real_winner !== data.poll_winner
                  ? `${data.poll_winner} → ${data.real_winner}`
                  : `${t('shyVoter.realWinner')}: ${data.real_winner}`
              }
              methodsChanged={data.real_winner !== data.poll_winner ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('shyVoter.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Winner comparison */}
          <div className="flex flex-wrap gap-2 items-center mb-3">
            <Badge variant="secondary" data-testid="poll-winner-badge">
              {t('shyVoter.pollWinner')}: {data.poll_winner}
            </Badge>
            <Badge
              variant={data.polls_wrong ? 'danger' : 'success'}
              data-testid="real-winner-badge"
            >
              {t('shyVoter.realWinner')}: {data.real_winner}
            </Badge>
            {data.polls_wrong && (
              <Alert
                variant="danger"
                className="inline-block py-1 px-2 mb-0"
                data-testid="polls-wrong-alert"
              >
                {t('shyVoter.pollsWrong')}
              </Alert>
            )}
            <Badge variant="info" data-testid="shy-candidate-badge">
              🤫 {t('shyVoter.shyLabel')}: {data.shy_candidate}
            </Badge>
          </div>

          {/* Systematic error badges */}
          <div className="flex flex-wrap gap-1 mb-3">
            {Object.entries(data.systematic_error).map(([c, err]) => (
              <Badge
                key={c}
                variant={err < -0.01 ? 'danger' : err > 0.01 ? 'warning' : 'light'}
                data-testid={`error-badge-${c}`}
                style={{ fontSize: '0.72rem' }}
              >
                {c}: {err >= 0 ? '+' : ''}
                {Math.round(err * 100)}pp
              </Badge>
            ))}
          </div>

          {/* Grouped bar chart: poll avg vs real */}
          <div className="mb-4" data-testid="comparison-bar-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('shyVoter.barTitle')}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis unit="%" tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="poll" name={t('shyVoter.poll')} fill="#adb5bd" opacity={0.8} />
                <Bar dataKey="real" name={t('shyVoter.real')} fill="#005CAB" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Poll timeline */}
          <div className="mb-4" data-testid="poll-timeline-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('shyVoter.timelineTitle')}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={timelineData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="x"
                  tickFormatter={(v: number) => (v <= data.poll_results.length ? `S${v}` : 'Réel')}
                  tick={{ fontSize: 10 }}
                />
                <YAxis unit="%" tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine
                  x={data.poll_results.length + 0.5}
                  stroke="#dc3545"
                  strokeDasharray="4 2"
                  label={{ value: 'J-0', fill: '#dc3545', fontSize: 9 }}
                />
                {candidateNames.map((c, i) => (
                  <Line
                    key={c}
                    type="monotone"
                    dataKey={c}
                    stroke={candColor(c, candidateNames)}
                    strokeWidth={c === data.shy_candidate ? 2.5 : 1.5}
                    strokeDasharray={c === data.shy_candidate ? undefined : '4 2'}
                    dot={(props: any) => {
                      const isReal = props.payload?.type === 'real';
                      if (!isReal)
                        return (
                          <circle
                            key={props.key}
                            cx={props.cx}
                            cy={props.cy}
                            r={2}
                            fill={candColor(c, candidateNames)}
                          />
                        );
                      return (
                        <circle
                          key={props.key}
                          cx={props.cx}
                          cy={props.cy}
                          r={5}
                          fill={candColor(c, candidateNames)}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      );
                    }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Systematic error table */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('shyVoter.errorTable')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50 mb-4"
            data-testid="error-table"
          >
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('shyVoter.candidate')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('shyVoter.poll')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('shyVoter.real')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('shyVoter.errorCol')}</th>
              </tr>
            </thead>
            <tbody>
              {candidateNames.map((c) => {
                const err = data.systematic_error[c] ?? 0;
                return (
                  <tr key={c}>
                    <td style={{ fontSize: '0.78rem' }}>
                      {c}
                      {c === data.shy_candidate && (
                        <Badge variant="warning" className="ms-1" style={{ fontSize: '0.6rem' }}>
                          🤫
                        </Badge>
                      )}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {Math.round((data.avg_poll_results[c] ?? 0) * 100)}%
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {Math.round((data.real_results[c] ?? 0) * 100)}%
                    </td>
                    <td
                      style={{
                        fontSize: '0.78rem',
                        color: err < 0 ? '#dc3545' : err > 0 ? '#198754' : '#6c757d',
                        fontWeight: 600,
                      }}
                    >
                      {err >= 0 ? '+' : ''}
                      {Math.round(err * 100)}pp
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('shyVoter.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}

      {/* Historical examples (always visible) */}
      <div className="mt-4" data-testid="historical-section">
        <div className="font-semibold mb-2" style={{ fontSize: '0.85rem' }}>
          {t('shyVoter.historicalTitle')}
        </div>
        <div className="flex flex-wrap gap-2">
          {HISTORICAL.map((h) => (
            <div
              key={h.year}
              className="border border-border rounded p-2"
              style={{ fontSize: '0.75rem', background: '#f8f9fa', maxWidth: 200 }}
            >
              <div>
                <strong>
                  {h.country} {h.year}
                </strong>{' '}
                — {h.event}
              </div>
              <div className="text-muted-foreground">{h.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ShyVoterPanel;
