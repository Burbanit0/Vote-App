import React, { useCallback, useState } from 'react';
import {
  Alert, Button, Card, Spinner, Table,
} from 'react-bootstrap';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import axios from 'axios';
import { useExpertMode } from '../../context/ExpertModeContext';
import { useMethodLabels } from './simulationConstants';
import { apiPath } from '../../api/apiVersion';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4434';

// ── Types ────────────────────────────────────────────────────────────────────

interface ManipResult {
  method: string;
  manipulability_rate: number | null;
  average_gain: number;
  num_manipulators: number;
  num_sampled: number;
  examples?: Array<{
    voter_id: number;
    sincere_rank: number;
    strategic_rank: number;
    sincere_winner?: string;
    strategic_winner?: string;
  }>;
  error?: string;
}

interface Props {
  baseParams: {
    num_candidates: number;
    num_voters: number;
    ideology_distribution: string;
  };
}

// ── Colour coding ─────────────────────────────────────────────────────────────

function rateColor(rate: number): string {
  if (rate < 5)  return '#1b5e20';   // green  — resistant
  if (rate < 20) return '#b35c00';   // orange — moderate
  return '#b71c1c';                  // red    — vulnerable
}

function rateLabel(rate: number): string {
  if (rate < 5)  return 'Résistante';
  if (rate < 20) return 'Modérée';
  return 'Vulnérable';
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function ManipTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d: ManipResult = payload[0].payload;
  const rate = d.manipulability_rate ?? 0;
  return (
    <div
      style={{
        background: 'var(--bs-body-bg, white)',
        border: '1px solid var(--bs-border-color, #dee2e6)',
        borderRadius: 8,
        padding: '10px 14px',
        fontSize: '0.82rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        maxWidth: 280,
      }}
    >
      <div className="fw-bold mb-1" style={{ color: rateColor(rate) }}>
        {rate.toFixed(1)} % — {rateLabel(rate)}
      </div>
      <div className="text-muted" style={{ lineHeight: 1.5 }}>
        {rate.toFixed(1)} % des électeurs échantillonnés peuvent améliorer
        leur résultat en ne votant pas sincèrement.
      </div>
      {d.average_gain > 0 && (
        <div className="mt-1">
          Gain moyen : <strong>{d.average_gain.toFixed(2)}</strong> rang(s)
        </div>
      )}
      <div className="text-muted mt-1" style={{ fontSize: '0.75rem' }}>
        {d.num_manipulators} / {d.num_sampled} électeurs testés
      </div>
    </div>
  );
}

// ── ManipulabilityChart ───────────────────────────────────────────────────────

const ManipulabilityChart: React.FC<Props> = ({ baseParams }) => {
  const { expertMode }   = useExpertMode();
  const methodLabels     = useMethodLabels();

  const [data,    setData]    = useState<ManipResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        num_candidates: String(baseParams.num_candidates),
        num_voters:     String(Math.min(500, baseParams.num_voters)), // cap for speed
        ideology:       baseParams.ideology_distribution,
        num_trials:     '200',
        methods:        'all',
      });
      const resp = await axios.get<{ results: ManipResult[] }>(
        `${API_BASE}${apiPath('simulations/manipulability')}?${params}`,
      );
      setData(resp.data.results.filter((r) => r.manipulability_rate !== null));
    } catch (e: any) {
      setError(e?.response?.data?.error ?? e?.message ?? 'Erreur lors de l\'analyse');
    } finally {
      setLoading(false);
    }
  }, [baseParams]);

  // Beginner mode: top 3 most resistant (lowest rate)
  const displayData = expertMode
    ? data
    : [...data].sort((a, b) => (a.manipulability_rate ?? 100) - (b.manipulability_rate ?? 100)).slice(0, 3);

  const chartData = displayData.map((d) => ({
    ...d,
    label: methodLabels[d.method] ?? d.method,
  }));

  return (
    <div>
      {/* ── Controls ── */}
      <div className="d-flex align-items-center gap-3 mb-3 flex-wrap">
        <Button
          variant="primary"
          onClick={runAnalysis}
          disabled={loading}
        >
          {loading
            ? <><Spinner size="sm" className="me-2" />Analyse…</>
            : '▶ Analyser la manipulabilité'}
        </Button>
        {data.length > 0 && (
          <small className="text-muted">
            {data.length} méthode{data.length !== 1 ? 's' : ''} · {baseParams.num_voters.toLocaleString()} électeurs
          </small>
        )}
      </div>

      {/* ── Beginner explanation ── */}
      {!expertMode && (
        <Alert variant="light" className="mb-3" style={{ fontSize: '0.85rem', borderLeft: '3px solid #0d6efd' }}>
          <strong>🎓 Le théorème de Gibbard-Satterthwaite</strong> démontre qu'aucune méthode de vote
          ne peut être complètement résistante à la manipulation. Ce graphique montre les{' '}
          <strong>3 méthodes les plus résistantes</strong> au vote stratégique.
          Un faible taux signifie que peu d'électeurs peuvent améliorer leur résultat en mentant sur leurs préférences.
        </Alert>
      )}

      {/* ── Error ── */}
      {error && <Alert variant="danger">{error}</Alert>}

      {/* ── Chart ── */}
      {chartData.length > 0 && (
        <Card className="mb-3">
          <Card.Header>
            <strong>Taux de manipulabilité par méthode</strong>
            <span className="text-muted ms-2" style={{ fontSize: '0.82rem' }}>
              — % d'électeurs qui peuvent améliorer leur résultat en votant stratégiquement
            </span>
          </Card.Header>
          <Card.Body>
            <div className="d-flex gap-4 mb-3 flex-wrap" style={{ fontSize: '0.82rem' }}>
              <span>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, background: '#1b5e20', marginRight: 4 }} />
                Résistante (&lt; 5 %)
              </span>
              <span>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, background: '#b35c00', marginRight: 4 }} />
                Modérée (5–20 %)
              </span>
              <span>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, background: '#b71c1c', marginRight: 4 }} />
                Vulnérable (&gt; 20 %)
              </span>
            </div>

            <ResponsiveContainer width="100%" height={chartData.length * 48 + 60}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 4, right: 60, left: 0, bottom: 16 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--bs-border-color, #dee2e6)" />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v} %`}
                  tick={{ fontSize: 11 }}
                  label={{
                    value: 'Taux de manipulation (%)',
                    position: 'insideBottom',
                    offset: -10,
                    fontSize: 11,
                    fill: '#6c757d',
                  }}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={110}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip content={<ManipTooltip />} />

                {/* Threshold reference line at 5 % */}
                <ReferenceLine
                  x={5}
                  stroke="#f59e0b"
                  strokeDasharray="5 3"
                  strokeWidth={2}
                  label={{
                    value: 'Seuil 5 %',
                    position: 'top',
                    fontSize: 11,
                    fill: '#b45309',
                  }}
                />

                <Bar dataKey="manipulability_rate" radius={[0, 4, 4, 0]} maxBarSize={28}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={rateColor(entry.manipulability_rate ?? 0)} />
                  ))}
                  <LabelList
                    dataKey="manipulability_rate"
                    position="right"
                    formatter={(v: unknown) => typeof v === 'number' ? `${v.toFixed(1)} %` : '—'}
                    style={{ fontSize: '0.8rem', fill: 'var(--bs-body-color, #333)' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card.Body>
        </Card>
      )}

      {/* ── Expert detail table ── */}
      {expertMode && data.length > 0 && (
        <Card>
          <Card.Header><strong>Détail par méthode</strong></Card.Header>
          <Card.Body className="p-0">
            <Table bordered size="sm" className="mb-0" style={{ fontSize: '0.82rem' }}>
              <thead className="table-light">
                <tr>
                  <th>Méthode</th>
                  <th className="text-center">Taux (%)</th>
                  <th className="text-center">Gain moyen (rangs)</th>
                  <th className="text-center">Manipulateurs</th>
                  <th className="text-center">Résistance</th>
                </tr>
              </thead>
              <tbody>
                {data.map((r) => {
                  const rate = r.manipulability_rate ?? 0;
                  return (
                    <tr key={r.method}>
                      <td className="fw-semibold">{methodLabels[r.method] ?? r.method}</td>
                      <td className="text-center" style={{ color: rateColor(rate) }}>
                        <strong>{rate.toFixed(1)}</strong>
                      </td>
                      <td className="text-center">{r.average_gain.toFixed(2)}</td>
                      <td className="text-center text-muted">
                        {r.num_manipulators} / {r.num_sampled}
                      </td>
                      <td className="text-center">
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: 12,
                            fontSize: '0.75rem',
                            background: rateColor(rate),
                            color: 'white',
                          }}
                        >
                          {rateLabel(rate)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </Card.Body>
        </Card>
      )}

      {!data.length && !loading && !error && (
        <Alert variant="info" style={{ fontSize: '0.88rem' }}>
          Cliquez sur <strong>Analyser la manipulabilité</strong> pour estimer le taux de manipulation
          de chaque méthode de vote sur la population configurée.
          L'analyse peut prendre quelques secondes.
        </Alert>
      )}
    </div>
  );
};

export default ManipulabilityChart;
