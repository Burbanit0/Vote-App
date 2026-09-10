/**
 * ChoiceOverloadPanel — simulates the paradox of choice (Schwartz 2004):
 * beyond a threshold of candidates, voters resort to heuristics instead
 * of their true preferences, degrading election quality.
 */
import React, { useCallback, useRef, useState } from 'react';
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
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

const DEFAULT_COUNTS = [2, 3, 5, 7, 10];

// ── Types ─────────────────────────────────────────────────────────────────────

interface NResult {
  num_candidates: number;
  mean_voter_regret: number;
  heuristic_voters: number;
  winner_by_method: Record<string, string | null>;
  condorcet_winner: string | null;
  methods_elect_condorcet: Record<string, boolean>;
}

interface OverloadData {
  results_by_n: NResult[];
  regret_curve: { n_candidates: number; regret: number }[];
  most_robust_method: string;
  least_robust_method: string;
  overload_threshold: number;
  heuristic_weights: { notoriety: number; primacy: number; partisan: number };
  pedagogical_note: string;
}

// ── Main panel ────────────────────────────────────────────────────────────────

const ChoiceOverloadPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [hNotoriety, setHNotoriety] = useState(0.2);
  const [hPrimacy, setHPrimacy] = useState(0.1);
  const [hPartisan, setHPartisan] = useState(0.2);
  const [threshold, setThreshold] = useState(5);
  const sim = $api.useMutation('post', '/api/v2/election/choice-overload');
  const data: OverloadData | null = (sim.data as OverloadData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('overload.error') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (hn: number, hp: number, hpa: number, thr: number) => {
      sim.mutate({
        body: {
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          candidate_counts: DEFAULT_COUNTS,
          overload_threshold: thr,
          heuristic_weights: { notoriety: hn, primacy: hp, partisan: hpa },
          methods: ['plurality', 'approval', 'borda', 'majority_judgment'],
        },
      });
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(hNotoriety, hPrimacy, hPartisan, threshold);

  const schedule = (hn: number, hp: number, hpa: number, thr: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(hn, hp, hpa, thr), 400);
  };

  // ── Line chart data ─────────────────────────────────────────────────────
  const lineData =
    data?.results_by_n.map((r) => ({
      n: r.num_candidates,
      regret: Math.round(r.mean_voter_regret * 1000) / 10,
      heuristic: Math.round(r.heuristic_voters * 100),
    })) ?? [];

  // ── Stacked heuristic bar data ──────────────────────────────────────────
  const totalH = data
    ? data.heuristic_weights.notoriety +
      data.heuristic_weights.primacy +
      data.heuristic_weights.partisan
    : hNotoriety + hPrimacy + hPartisan;

  const barData =
    data?.results_by_n.map((r) => {
      const hp = r.heuristic_voters;
      const th = totalH || 1;
      return {
        n: r.num_candidates,
        sincere: Math.round((1 - hp) * 100),
        notoriety: Math.round(hp * (data.heuristic_weights.notoriety / th) * 100),
        primacy: Math.round(hp * (data.heuristic_weights.primacy / th) * 100),
        partisan: Math.round(hp * (data.heuristic_weights.partisan / th) * 100),
      };
    }) ?? [];

  // ── Method table data ───────────────────────────────────────────────────
  const methods = data ? Object.keys(data.results_by_n[0]?.winner_by_method ?? {}) : [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('overload.threshold')}: <strong>{threshold}</strong>
          </label>
          <Range
            data-testid="threshold-slider"
            min={2}
            max={10}
            step={1}
            value={threshold}
            onChange={(e) => {
              setThreshold(Number(e.target.value));
              schedule(hNotoriety, hPrimacy, hPartisan, Number(e.target.value));
            }}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            🎤 {t('overload.notoriety')}: <strong>{Math.round(hNotoriety * 100)}%</strong>
          </label>
          <Range
            data-testid="notoriety-slider"
            min={0}
            max={0.5}
            step={0.05}
            value={hNotoriety}
            onChange={(e) => {
              setHNotoriety(Number(e.target.value));
              schedule(Number(e.target.value), hPrimacy, hPartisan, threshold);
            }}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            1️⃣ {t('overload.primacy')}: <strong>{Math.round(hPrimacy * 100)}%</strong>
          </label>
          <Range
            data-testid="primacy-slider"
            min={0}
            max={0.5}
            step={0.05}
            value={hPrimacy}
            onChange={(e) => {
              setHPrimacy(Number(e.target.value));
              schedule(hNotoriety, Number(e.target.value), hPartisan, threshold);
            }}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            🏳️ {t('overload.partisan')}: <strong>{Math.round(hPartisan * 100)}%</strong>
          </label>
          <Range
            data-testid="partisan-slider"
            min={0}
            max={0.5}
            step={0.05}
            value={hPartisan}
            onChange={(e) => {
              setHPartisan(Number(e.target.value));
              schedule(hNotoriety, hPrimacy, Number(e.target.value), threshold);
            }}
          />
        </Col>
      </Row>

      <div className="flex gap-2 mb-3 flex-wrap">
        <Button variant="primary" onClick={handleSimulate} disabled={loading}>
          {loading ? <Spinner size="sm" /> : t('overload.run')}
        </Button>
        {data &&
          data.results_by_n.length > 0 &&
          (() => {
            // Take the last/largest N as the "overloaded" scenario for the pin
            const overloaded = data.results_by_n[data.results_by_n.length - 1];
            return (
              <PinToCentralButton
                type="overload"
                icon="🤯"
                label={`${t('overload.run')} (n=${overloaded.num_candidates})`}
                summary={`${t('overload.run')}: ${overloaded.heuristic_voters} heuristic voters`}
                winnersByMethod={overloaded.winner_by_method}
              />
            );
          })()}
      </div>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('overload.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Robustness badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="success" data-testid="most-robust-badge">
              {t('overload.mostRobust')}: {data.most_robust_method}
            </Badge>
            <Badge variant="danger" data-testid="least-robust-badge">
              {t('overload.leastRobust')}: {data.least_robust_method}
            </Badge>
            <Badge variant="info">
              {t('overload.threshold')} = {data.overload_threshold}
            </Badge>
          </div>

          {/* Dual-axis LineChart */}
          <div className="mb-4" data-testid="overload-line-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('overload.lineTitle')}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={lineData} margin={{ top: 4, right: 40, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="n"
                  label={{
                    value: t('overload.nCandidates'),
                    position: 'insideBottom',
                    offset: -2,
                    fontSize: 10,
                  }}
                />
                <YAxis yAxisId="left" domain={[0, 'auto']} tick={{ fontSize: 10 }} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[0, 100]}
                  unit="%"
                  tick={{ fontSize: 10 }}
                />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine
                  yAxisId="left"
                  x={data.overload_threshold}
                  stroke="#dc3545"
                  strokeDasharray="4 2"
                  label={{ value: t('overload.thresholdLine'), fill: '#dc3545', fontSize: 9 }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="regret"
                  name={t('overload.regret')}
                  stroke="#dc3545"
                  strokeWidth={2}
                  dot
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="heuristic"
                  name={t('overload.heuristicVoters')}
                  stroke="#fd7e14"
                  strokeWidth={2}
                  dot
                  strokeDasharray="4 2"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Stacked heuristic breakdown */}
          <div className="mb-4" data-testid="heuristic-bar-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('overload.barTitle')}
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={barData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="n" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 10 }} />
                <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="sincere" name={t('overload.sincere')} stackId="a" fill="#198754" />
                <Bar
                  dataKey="notoriety"
                  name={t('overload.notoriety')}
                  stackId="a"
                  fill="#fd7e14"
                />
                <Bar dataKey="primacy" name={t('overload.primacy')} stackId="a" fill="#6f42c1" />
                <Bar dataKey="partisan" name={t('overload.partisan')} stackId="a" fill="#dc3545" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Method robustness table */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('overload.tableTitle')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50 mb-3"
            data-testid="method-table"
          >
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>N</th>
                <th style={{ fontSize: '0.78rem' }}>{t('overload.regret')}</th>
                <th style={{ fontSize: '0.78rem' }}>H%</th>
                {methods.map((m) => (
                  <th key={m} style={{ fontSize: '0.78rem' }}>
                    <code>{m}</code>
                    {m === data.most_robust_method && (
                      <Badge variant="success" className="ms-1" style={{ fontSize: '0.55rem' }}>
                        ✓
                      </Badge>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.results_by_n.map((r) => (
                <tr
                  key={r.num_candidates}
                  style={{
                    background: r.num_candidates > data.overload_threshold ? '#fff5f5' : undefined,
                  }}
                >
                  <td style={{ fontSize: '0.78rem', fontWeight: 600 }}>{r.num_candidates}</td>
                  <td
                    style={{
                      fontSize: '0.78rem',
                      color: r.mean_voter_regret > 0.05 ? '#dc3545' : '#6c757d',
                    }}
                  >
                    {Math.round(r.mean_voter_regret * 1000) / 10}
                  </td>
                  <td style={{ fontSize: '0.78rem' }}>{Math.round(r.heuristic_voters * 100)}%</td>
                  {methods.map((m) => (
                    <td key={m} style={{ fontSize: '0.78rem' }}>
                      {r.winner_by_method[m] ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('overload.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default ChoiceOverloadPanel;
