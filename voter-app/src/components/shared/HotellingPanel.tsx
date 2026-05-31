/**
 * HotellingPanel — Hotelling-Downs Nash equilibrium animation.
 *
 * Simulates how rational candidates move to maximise their vote share.
 * With Plurality they converge to the median voter (Downs 1957).
 * With other methods (Approval, Borda) they may disperse or oscillate.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import { useElection } from '../../context/ElectionContext';
import { $api } from '../../api/hooks';
import { apiClient } from '../../api/client';

// ── Types ─────────────────────────────────────────────────────────────────────

interface CandPos    { name: string; x: number; y: number }
interface Iteration  {
  step:                  number;
  candidates:            CandPos[];
  scores:                Record<string, number>;
  converged_candidates:  string[];
}

interface HotellingData {
  iterations:       Iteration[];
  converged:        boolean;
  convergence_step: number | null;
  final_positions:  CandPos[];
  equilibrium_type: 'center_convergence' | 'dispersed' | 'unstable';
  voters:           { x: number; y: number }[];
  candidates:       string[];
  method:           string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]) {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── SVG constants ─────────────────────────────────────────────────────────────

const SVG_W = 400;
const SVG_H = 380;
const PAD   = 24;

function dx(v: number) { return PAD + ((v + 1) / 2) * (SVG_W - 2 * PAD); }
function dy(v: number) { return PAD + ((1 - v) / 2) * (SVG_H - 2 * PAD); }

// ── Comparison methods ────────────────────────────────────────────────────────

const COMPARE_METHODS = ['plurality', 'borda', 'irv', 'approval'] as const;

// ── Main component ────────────────────────────────────────────────────────────

const HotellingPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [method,    setMethod]    = useState('plurality');
  const [numIter,   setNumIter]   = useState(10);
  const [stepSize,  setStepSize]  = useState(0.05);
  const sim = $api.useMutation('post', '/api/v2/election/hotelling');
  const data: HotellingData | null = (sim.data as HotellingData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('hotelling.error') : null;
  const [stepIdx,   setStepIdx]   = useState(0);
  const [playing,   setPlaying]   = useState(false);

  // Multi-method comparison
  const [comparing,    setComparing]    = useState(false);
  const [compareData,  setCompareData]  = useState<Record<string, HotellingData>>({});

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const candidateNames = config.candidates.map(c => c.name);

  function run(m = method) {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPlaying(false); setStepIdx(0);
    sim.mutate({ body: {
      candidates:     config.candidates,
      num_voters:     config.num_voters,
      ideology:       config.ideology,
      seed:           config.seed,
      method:         m,
      num_iterations: numIter,
      step_size:      stepSize,
    } });
  }

  async function runComparison() {
    setComparing(true);
    const results: Record<string, HotellingData> = {};
    for (const m of COMPARE_METHODS) {
      const { data: res } = await apiClient.POST('/api/v2/election/hotelling', {
        body: {
          candidates:     config.candidates,
          num_voters:     config.num_voters,
          ideology:       config.ideology,
          seed:           config.seed,
          method:         m,
          num_iterations: numIter,
          step_size:      stepSize,
        },
      });
      if (res) results[m] = res as unknown as HotellingData;
    }
    setCompareData(results);
    setComparing(false);
  }

  // Auto-play
  useEffect(() => {
    if (!playing || !data) return;
    const maxStep = data.iterations.length - 1;
    if (stepIdx >= maxStep) { setPlaying(false); return; }
    timerRef.current = setTimeout(() => setStepIdx(s => s + 1), 800);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, stepIdx, data]);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  const snap = data?.iterations[stepIdx];

  // Background colour based on convergence
  const bgColor = data
    ? data.equilibrium_type === 'center_convergence' ? '#f0fff4'
    : data.equilibrium_type === 'dispersed'          ? '#fff8e1'
    : '#fff3f3'
    : 'transparent';

  // Pedagogical message
  const pedagMsg = useCallback(() => {
    if (!data) return '';
    const fp = data.final_positions;
    if (data.equilibrium_type === 'center_convergence') {
      const xs = fp.map(p => p.x.toFixed(2)).join(', ');
      return t('hotelling.pedagogicalCenter', { method, xs });
    }
    if (data.equilibrium_type === 'dispersed') {
      const pairs = fp.map(p => `${p.name} (x=${p.x.toFixed(2)})`).join(', ');
      return t('hotelling.pedagogicalDispersed', { method, pairs });
    }
    return t('hotelling.pedagogicalUnstable', { method });
  }, [data, method, t]);

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">{t('hotelling.method')}</Form.Label>
          <Form.Select size="sm" value={method} onChange={e => setMethod(e.target.value)}>
            {['plurality', 'borda', 'irv', 'approval'].map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </Form.Select>
        </Col>
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">
            {t('hotelling.iterations')}: <strong>{numIter}</strong>
          </Form.Label>
          <Form.Range min={1} max={20} step={1} value={numIter}
            onChange={e => setNumIter(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={2}>
          <Form.Label className="small mb-0">
            {t('hotelling.stepSize')}: <strong>{stepSize.toFixed(2)}</strong>
          </Form.Label>
          <Form.Range min={0.01} max={0.15} step={0.01} value={stepSize}
            onChange={e => setStepSize(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={2}>
          <Button variant="primary" className="w-100" onClick={() => run()} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `▶ ${t('hotelling.run')}`}
          </Button>
        </Col>
        <Col xs={12} sm={2}>
          <Button variant="outline-secondary" className="w-100" size="sm"
            onClick={runComparison} disabled={comparing || loading}>
            {comparing ? <Spinner size="sm" /> : t('hotelling.compare')}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('hotelling.prompt')}</Alert>}

      {data && (
        <Row className="g-3">
          {/* Left: animated SVG */}
          <Col xs={12} lg={7}>
            {/* Convergence badge + play */}
            <div className="d-flex align-items-center gap-2 mb-2 flex-wrap">
              <Button size="sm" variant={playing ? 'warning' : 'success'}
                onClick={() => setPlaying(!playing)} data-testid="play-button">
                {playing ? '⏸' : '▶'} {t('hotelling.step')} {stepIdx}/{data.iterations.length - 1}
              </Button>
              <Badge
                bg={data.converged ? 'success' : 'danger'}
                data-testid="convergence-badge"
              >
                {data.converged
                  ? `✓ ${t('hotelling.convergedAt')} step ${data.convergence_step}`
                  : `✗ ${t('hotelling.noConvergence')}`}
              </Badge>
              <Badge bg="secondary" style={{ fontSize: '0.7rem' }}>
                {t(`hotelling.eq_${data.equilibrium_type}`)}
              </Badge>
            </div>

            <Form.Range
              min={0} max={data.iterations.length - 1} step={1} value={stepIdx}
              onChange={e => { setPlaying(false); setStepIdx(Number(e.target.value)); }}
              className="mb-2"
              data-testid="step-slider"
            />

            {/* SVG canvas */}
            <svg
              data-testid="hotelling-svg"
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              width="100%"
              style={{
                display: 'block',
                background: bgColor,
                borderRadius: 8,
                transition: 'background 0.5s',
                maxHeight: 380,
              }}
            >
              {/* Grid */}
              <line x1={SVG_W / 2} y1={PAD} x2={SVG_W / 2} y2={SVG_H - PAD} stroke="#dee2e6" strokeWidth={1} />
              <line x1={PAD} y1={SVG_H / 2} x2={SVG_W - PAD} y2={SVG_H / 2} stroke="#dee2e6" strokeWidth={1} />
              <rect x={PAD} y={PAD} width={SVG_W - 2 * PAD} height={SVG_H - 2 * PAD}
                fill="none" stroke="#ced4da" strokeWidth={0.8} />
              <text x={PAD}          y={SVG_H - 6} fontSize={9} fill="#adb5bd">← Gauche</text>
              <text x={SVG_W - PAD}  y={SVG_H - 6} textAnchor="end" fontSize={9} fill="#adb5bd">Droite →</text>

              {/* Voter dots */}
              {data.voters.map((v, i) => (
                <circle key={i} cx={dx(v.x)} cy={dy(v.y)} r={2}
                  fill="#adb5bd" fillOpacity={0.3} />
              ))}

              {/* Trajectories (polylines) */}
              {candidateNames.map(name => {
                const pts = data.iterations
                  .slice(0, stepIdx + 1)
                  .map(it => {
                    const c = it.candidates.find(c => c.name === name);
                    return c ? `${dx(c.x)},${dy(c.y)}` : null;
                  })
                  .filter(Boolean)
                  .join(' ');
                return pts ? (
                  <polyline key={name} points={pts}
                    fill="none"
                    stroke={candColor(name, candidateNames)}
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                    strokeOpacity={0.5}
                    data-testid={`trajectory-${name}`}
                  />
                ) : null;
              })}

              {/* Candidate stars — animated via CSS transition */}
              {snap && candidateNames.map(name => {
                const c    = snap.candidates.find(c => c.name === name);
                if (!c) return null;
                const cx   = dx(c.x);
                const cy   = dy(c.y);
                const color = candColor(name, candidateNames);
                const isConverged = snap.converged_candidates.includes(name);
                return (
                  <g key={name} transform={`translate(${cx},${cy})`}
                    style={{ transition: 'transform 0.6s ease' }}>
                    {isConverged && (
                      <circle r={14} fill="none" stroke={color} strokeWidth={1.5} strokeDasharray="3 2" />
                    )}
                    <text textAnchor="middle" dominantBaseline="central"
                      fontSize={20} fill={color} stroke="#fff" strokeWidth={0.7}
                      style={{ userSelect: 'none' }}>★</text>
                    <text y={-18} textAnchor="middle" fontSize={10} fontWeight={600}
                      fill={color} stroke="#fff" strokeWidth={2.5} paintOrder="stroke"
                      style={{ userSelect: 'none' }}>
                      {name}{isConverged ? ' ✓' : ''}
                    </text>
                    <text y={16} textAnchor="middle" fontSize={8} fill={color}>
                      {Math.round((snap.scores[name] ?? 0) * 100)}%
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Pedagogical message */}
            {data && (
              <Alert
                variant={data.equilibrium_type === 'center_convergence' ? 'success'
                  : data.equilibrium_type === 'dispersed' ? 'warning' : 'danger'}
                className="mt-2 py-2" style={{ fontSize: '0.82rem' }}
                data-testid="pedagogical-msg"
              >
                {pedagMsg()}
              </Alert>
            )}
          </Col>

          {/* Right: comparison table + score readout */}
          <Col xs={12} lg={5}>
            {/* Current scores */}
            {snap && (
              <div className="mb-3">
                <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                  {t('hotelling.scores')} — {t('hotelling.step')} {snap.step}
                </div>
                {candidateNames.map(name => {
                  const pct = Math.round((snap.scores[name] ?? 0) * 100);
                  return (
                    <div key={name} className="d-flex align-items-center gap-2 mb-1">
                      <span style={{ minWidth: 65, color: candColor(name, candidateNames), fontSize: '0.8rem' }}>{name}</span>
                      <div style={{ flex: 1, height: 10, background: '#e9ecef', borderRadius: 5, overflow: 'hidden' }}>
                        <div style={{
                          width: `${pct}%`, height: '100%',
                          background: candColor(name, candidateNames),
                          borderRadius: 5, transition: 'width 0.4s',
                        }} />
                      </div>
                      <span style={{ minWidth: 32, fontSize: '0.75rem' }}>{pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Final positions table */}
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('hotelling.finalPositions')}
            </div>
            <Table size="sm" bordered style={{ fontSize: '0.78rem' }}>
              <thead className="table-light">
                <tr>
                  <th>{t('common.method')}</th>
                  {candidateNames.map(n => <th key={n}>{n} (x, y)</th>)}
                  <th>{t('hotelling.eq')}</th>
                </tr>
              </thead>
              <tbody>
                {/* Current method result */}
                <tr style={{ background: '#e8f4ff' }}>
                  <td className="fw-semibold">{method}</td>
                  {data.final_positions.map(p => (
                    <td key={p.name}>({p.x.toFixed(2)}, {p.y.toFixed(2)})</td>
                  ))}
                  <td>
                    <Badge bg={data.converged ? 'success' : 'danger'}
                      style={{ fontSize: '0.65rem' }}>
                      {t(`hotelling.eq_short_${data.equilibrium_type}`)}
                    </Badge>
                  </td>
                </tr>
                {/* Multi-method comparison rows */}
                {Object.entries(compareData).filter(([m]) => m !== method).map(([m, d]) => (
                  <tr key={m}>
                    <td>{m}</td>
                    {d.final_positions.map(p => (
                      <td key={p.name}>({p.x.toFixed(2)}, {p.y.toFixed(2)})</td>
                    ))}
                    <td>
                      <Badge bg={d.converged ? 'success' : 'danger'}
                        style={{ fontSize: '0.65rem' }}>
                        {t(`hotelling.eq_short_${d.equilibrium_type}`)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {Object.keys(compareData).length === 0 && (
              <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                {t('hotelling.compareHint')}
              </div>
            )}
          </Col>
        </Row>
      )}
    </div>
  );
};

export default HotellingPanel;
