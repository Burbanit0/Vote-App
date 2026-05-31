/**
 * PolarizationPanel — Esteban-Ray polarization index vs electoral quality.
 *
 * Shows how increasing polarization degrades:
 *   - Condorcet winner existence rate
 *   - Inter-method agreement
 *   - Winner stability
 * And reveals which methods are most robust under polarized electorates.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, Label,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PolarResult {
  ideology:           string;
  polarization_index: number;
  condorcet_rate:     number;
  agreement_rate:     number;
  winner_stability:   number;
  best_method:        string;
  worst_method:       string;
  method_regrets:     Record<string, number>;
}

interface PolarData {
  results:      PolarResult[];
  key_findings: string[];
}

// ── Palette ───────────────────────────────────────────────────────────────────

const IDEOLOGY_COLORS: Record<string, string> = {
  centrist:    '#007A33',
  random:      '#005CAB',
  left_skewed: '#9b59b6',
  right_skewed:'#e67e22',
  polarized:   '#dc3545',
};

const AVAILABLE_IDEOLOGIES = ['centrist', 'random', 'left_skewed', 'right_skewed', 'polarized'];

// ── Heatmap SVG ───────────────────────────────────────────────────────────────

interface HeatmapProps {
  results:    PolarResult[];
  metric:     'agreement_rate' | 'condorcet_rate';
}

const PolarHeatmap: React.FC<HeatmapProps> = ({ results, metric }) => {
  const { t } = useTranslation();
  if (results.length === 0) return null;

  const sorted    = [...results].sort((a, b) => a.polarization_index - b.polarization_index);
  const allMethods = Array.from(
    new Set(sorted.flatMap(r => Object.keys(r.method_regrets)))
  ).sort();

  const CELL_W = 60;
  const CELL_H = 24;
  const LABEL_W = 110;
  const W = LABEL_W + sorted.length * CELL_W + 10;
  const H = allMethods.length * CELL_H + 50;

  function cellColor(value: number): string {
    const r = Math.round(183 + (1 - value) * 72);
    const g = Math.round(28  + value * 94);
    return `rgb(${r},${g},28)`;
  }

  return (
    <svg
      data-testid="polarization-heatmap"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ display: 'block' }}
    >
      {/* Column headers (ideologies) */}
      {sorted.map((r, ci) => (
        <text key={r.ideology}
          x={LABEL_W + ci * CELL_W + CELL_W / 2}
          y={20} textAnchor="middle" fontSize={8}
          fill={IDEOLOGY_COLORS[r.ideology] ?? '#6c757d'}
        >
          {r.ideology.split('_')[0]}
        </text>
      ))}
      <text x={LABEL_W} y={34} fontSize={7} fill="#6c757d">
        P={sorted[0]?.polarization_index.toFixed(2)}
      </text>
      <text x={LABEL_W + (sorted.length - 1) * CELL_W} y={34}
        textAnchor="end" fontSize={7} fill="#6c757d">
        P={sorted[sorted.length - 1]?.polarization_index.toFixed(2)}
      </text>

      {/* Rows (methods) */}
      {allMethods.map((method, ri) => (
        <g key={method}>
          <text x={LABEL_W - 4} y={44 + ri * CELL_H + CELL_H / 2}
            textAnchor="end" dominantBaseline="central" fontSize={9} fill="currentColor">
            {method.replace(/_/g, ' ')}
          </text>
          {sorted.map((r, ci) => {
            // For heatmap use agreement_rate proxy: low regret = high quality
            const regret = r.method_regrets[method];
            const maxR   = Math.max(...sorted.map(s => s.method_regrets[method] ?? 0));
            const val    = regret != null && maxR > 0 ? 1 - regret / maxR : 0.5;
            return (
              <rect key={r.ideology}
                x={LABEL_W + ci * CELL_W + 1}
                y={44 + ri * CELL_H + 1}
                width={CELL_W - 2} height={CELL_H - 2}
                rx={2}
                fill={cellColor(val)}
                data-testid="heatmap-cell"
              >
                <title>
                  {method} / {r.ideology}: regret={regret?.toFixed(4) ?? '—'}
                </title>
              </rect>
            );
          })}
        </g>
      ))}
    </svg>
  );
};

// ── Linear trend line ─────────────────────────────────────────────────────────

function linearRegression(points: { x: number; y: number }[]) {
  const n  = points.length;
  if (n < 2) return null;
  const mx = points.reduce((s, p) => s + p.x, 0) / n;
  const my = points.reduce((s, p) => s + p.y, 0) / n;
  const b  = points.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0)
           / points.reduce((s, p) => s + (p.x - mx) ** 2, 0.001);
  const a  = my - b * mx;
  return { a, b };  // y = a + b*x
}

// ── Main component ────────────────────────────────────────────────────────────

const PolarizationPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [selectedIdeologies, setSelectedIdeologies] = useState<string[]>(AVAILABLE_IDEOLOGIES);
  const [numSims,  setNumSims]  = useState(15);
  const sim = $api.useMutation('post', '/api/v2/election/polarization');
  const data: PolarData | null = (sim.data as PolarData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('polarization.error') : null;

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const run = useCallback((ideologies: string[], sims: number) => {
    if (ideologies.length === 0) return;
    sim.mutate({ body: {
      candidates:      config.candidates,
      num_voters:      Math.min(config.num_voters, 150),
      ideology_range:  ideologies,
      seed:            config.seed,
      num_simulations: sims,
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, t, sim]);

  const handleSimsChange = (v: number) => {
    setNumSims(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(selectedIdeologies, v), 500);
  };

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const toggleIdeology = (id: string) => {
    setSelectedIdeologies(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const sorted = data
    ? [...data.results].sort((a, b) => a.polarization_index - b.polarization_index)
    : [];

  const scatterPoints = sorted.map(r => ({
    x:    round2(r.polarization_index),
    y:    round2(r.condorcet_rate * 100),
    name: r.ideology,
  }));

  const trend = linearRegression(scatterPoints.map(p => ({ x: p.x, y: p.y })));

  // Threshold where condorcet rate < 70%
  const threshold = sorted.find(r => r.condorcet_rate < 0.7);

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={6}>
          <Form.Label className="small mb-1">{t('polarization.ideologies')}</Form.Label>
          <div className="d-flex flex-wrap gap-1">
            {AVAILABLE_IDEOLOGIES.map(id => (
              <Badge
                key={id}
                style={{
                  cursor:     'pointer',
                  background: selectedIdeologies.includes(id)
                    ? IDEOLOGY_COLORS[id] ?? '#6c757d'
                    : '#dee2e6',
                  color: selectedIdeologies.includes(id) ? '#fff' : '#6c757d',
                  fontSize: '0.72rem',
                }}
                onClick={() => toggleIdeology(id)}
                data-testid={`ideology-badge-${id}`}
              >
                {id}
              </Badge>
            ))}
          </div>
        </Col>
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">
            {t('polarization.numSims')}: <strong>{numSims}</strong>
          </Form.Label>
          <Form.Range min={5} max={50} step={5} value={numSims}
            onChange={e => handleSimsChange(Number(e.target.value))}
            data-testid="sims-slider"
          />
        </Col>
        <Col xs={12} sm={3}>
          <Button variant="primary" className="w-100"
            onClick={() => run(selectedIdeologies, numSims)} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `📊 ${t('polarization.run')}`}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('polarization.prompt')}</Alert>}

      {loading && (
        <div className="text-center py-4 text-muted">
          <Spinner className="me-2" />
          {t('polarization.computing')}
        </div>
      )}

      {data && !loading && (
        <>
          {/* Key findings */}
          <Alert variant="info" className="py-2 mb-3" style={{ fontSize: '0.82rem' }}>
            <strong>{t('polarization.findings')}</strong>
            <ul className="mb-0 mt-1">
              {data.key_findings.map((f, i) => (
                <li key={i} data-testid="finding-item">{f}</li>
              ))}
            </ul>
          </Alert>

          <Row className="g-3">
            {/* Scatter plot */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('polarization.scatterTitle')}
              </div>
              <div style={{ height: 260 }} data-testid="scatter-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                    <XAxis dataKey="x" type="number" name="Polarisation (P)"
                      domain={[0, 'auto']} tick={{ fontSize: 10 }}>
                      <Label value="Indice Esteban-Ray (P)" offset={-12}
                        position="insideBottom" style={{ fontSize: 10, fill: '#6c757d' }} />
                    </XAxis>
                    <YAxis dataKey="y" type="number" domain={[0, 100]}
                      unit="%" tick={{ fontSize: 10 }}>
                      <Label value="Taux CW %" angle={-90} position="insideLeft"
                        style={{ fontSize: 10, fill: '#6c757d' }} />
                    </YAxis>
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      formatter={(v: number, n: string) => [
                        n === 'x' ? v.toFixed(3) : `${v}%`, n === 'x' ? 'P' : 'Condorcet %',
                      ]}
                      labelFormatter={() => ''}
                    />
                    {/* One Scatter per ideology for colour */}
                    {scatterPoints.map(pt => (
                      <Scatter
                        key={pt.name}
                        name={pt.name}
                        data={[pt]}
                        fill={IDEOLOGY_COLORS[pt.name] ?? '#888'}
                        data-testid={`scatter-point-${pt.name}`}
                      />
                    ))}
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              {/* Trend line overlay note */}
              {trend && (
                <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
                  {t('polarization.trendNote', { slope: (trend.b * 100).toFixed(1) })}
                </div>
              )}

              {/* Threshold badge */}
              {threshold && (
                <Badge bg="danger" className="mt-1" data-testid="threshold-badge"
                  style={{ fontSize: '0.72rem' }}>
                  {t('polarization.threshold', {
                    p:   threshold.polarization_index.toFixed(2),
                    pct: Math.round((1 - threshold.condorcet_rate) * 100),
                  })}
                </Badge>
              )}

              {/* Summary table */}
              <div className="mt-2" style={{ fontSize: '0.76rem' }}>
                <div className="d-flex flex-wrap gap-2">
                  {sorted.map(r => (
                    <span key={r.ideology}>
                      <span style={{
                        display: 'inline-block', width: 8, height: 8,
                        borderRadius: '50%', background: IDEOLOGY_COLORS[r.ideology],
                        marginRight: 3,
                      }} />
                      {r.ideology}: P={r.polarization_index.toFixed(2)} ·
                      CW {Math.round(r.condorcet_rate * 100)}%
                    </span>
                  ))}
                </div>
              </div>
            </Col>

            {/* Heatmap */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('polarization.heatmapTitle')}
              </div>
              <div className="border rounded p-2">
                <PolarHeatmap results={sorted} metric="agreement_rate" />
                <div className="d-flex justify-content-between mt-1"
                  style={{ fontSize: '0.68rem', color: '#6c757d' }}>
                  <span style={{ color: '#dc3545' }}>■ {t('polarization.highRegret')}</span>
                  <span style={{ color: '#007A33' }}>■ {t('polarization.lowRegret')}</span>
                </div>
              </div>

              {/* Best/worst method badges */}
              <div className="mt-2 d-flex flex-wrap gap-2">
                {sorted.slice(-2).map(r => (
                  <React.Fragment key={r.ideology}>
                    {r.best_method && (
                      <Badge bg="success" style={{ fontSize: '0.7rem' }}
                        data-testid={`best-badge-${r.ideology}`}>
                        {r.ideology}: 🏆 {r.best_method}
                      </Badge>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

function round2(v: number) { return Math.round(v * 100) / 100; }

export default PolarizationPanel;
