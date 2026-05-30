/**
 * PowerIndicesPanel — Shapley-Shubik (1954) & Banzhaf (1965) power indices.
 * Demonstrates that electoral weight ≠ coalition bargaining power.
 */
import React, { useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PartyInput {
  name:   string;
  seats:  number;
  pariah: boolean;
  color:  string;
}

interface PartyResult {
  name:           string;
  seats:          number;
  seat_pct:       number;
  shapley_index:  number;
  banzhaf_index:  number;
  power_ratio:    number;
  critical_count: number;
  pivot_count:    number;
  is_pariah:      boolean;
}

interface Coalition {
  parties: string[];
  seats:   number;
  minimal: boolean;
}

interface PowerData {
  total_seats:        number;
  majority_threshold: number;
  parties:            PartyResult[];
  viable_coalitions:  Coalition[];
  power_surprises:    string[];
  pedagogical_note:   string;
}

// ── Colour palette ────────────────────────────────────────────────────────────

const PALETTE = [
  '#0d6efd', '#dc3545', '#198754', '#fd7e14',
  '#6f42c1', '#20c997', '#ffc107', '#0dcaf0',
];

// ── Preset scenarios ──────────────────────────────────────────────────────────

const PRESETS: Record<string, { label: string; parties: Omit<PartyInput, 'color'>[] }> = {
  france2022: {
    label: '🇫🇷 France 2022',
    parties: [
      { name: 'NUPES', seats: 131, pariah: false },
      { name: 'Ensemble', seats: 245, pariah: false },
      { name: 'RN', seats: 89, pariah: true },
      { name: 'LR', seats: 61, pariah: false },
      { name: 'Divers', seats: 51, pariah: false },
    ],
  },
  germany2021: {
    label: '🇩🇪 Allemagne 2021',
    parties: [
      { name: 'SPD', seats: 206, pariah: false },
      { name: 'CDU/CSU', seats: 197, pariah: false },
      { name: 'Grünen', seats: 118, pariah: false },
      { name: 'FDP', seats: 92, pariah: false },
      { name: 'AfD', seats: 83, pariah: true },
      { name: 'Linke', seats: 39, pariah: false },
    ],
  },
  pivot_paradox: {
    label: '⚖️ Paradoxe pivot',
    parties: [
      { name: 'Grand', seats: 45, pariah: false },
      { name: 'Moyen', seats: 35, pariah: false },
      { name: 'Petit', seats: 20, pariah: false },
    ],
  },
};

// ── SVG Hemicycle coloured by power ──────────────────────────────────────────

interface HemicycleProps {
  parties: PartyResult[];
  colors:  Record<string, string>;
}

const PowerHemicycle: React.FC<HemicycleProps> = ({ parties, colors }) => {
  const W = 340, H = 200, cx = W / 2, cy = H - 10;
  const R_outer = 150, R_inner = 80;
  const totalPower = parties.reduce((s, p) => s + p.shapley_index, 0);

  const slices: React.ReactElement[] = [];
  let angle = Math.PI;

  parties.forEach((p) => {
    const share = totalPower > 0 ? p.shapley_index / totalPower : 1 / parties.length;
    const sweep = share * Math.PI;
    const aEnd = angle + sweep;

    const x1o = cx + R_outer * Math.cos(angle), y1o = cy + R_outer * Math.sin(angle);
    const x2o = cx + R_outer * Math.cos(aEnd),  y2o = cy + R_outer * Math.sin(aEnd);
    const x1i = cx + R_inner * Math.cos(angle), y1i = cy + R_inner * Math.sin(angle);
    const x2i = cx + R_inner * Math.cos(aEnd),  y2i = cy + R_inner * Math.sin(aEnd);

    const large = sweep > Math.PI ? 1 : 0;
    const d = [
      `M ${x1o} ${y1o}`,
      `A ${R_outer} ${R_outer} 0 ${large} 1 ${x2o} ${y2o}`,
      `L ${x2i} ${y2i}`,
      `A ${R_inner} ${R_inner} 0 ${large} 0 ${x1i} ${y1i}`,
      'Z',
    ].join(' ');

    const fill = p.shapley_index === 0 ? '#adb5bd' : (colors[p.name] ?? '#6c757d');
    slices.push(
      <path key={p.name} d={d} fill={fill} stroke="#fff" strokeWidth={1.5}
        opacity={0.9}>
        <title>{p.name}: Shapley {Math.round(p.shapley_index * 100)}%</title>
      </path>
    );
    angle = aEnd;
  });

  return (
    <svg data-testid="power-hemicycle" width={W} height={H}
      style={{ display: 'block', margin: '0 auto' }}>
      {slices}
      <text x={cx} y={cy - 20} textAnchor="middle"
        style={{ fontSize: 11, fill: '#495057', fontWeight: 600 }}>
        Pouvoir Shapley
      </text>
    </svg>
  );
};

// ── Scatter: seats% vs Shapley% ───────────────────────────────────────────────

interface ScatterProps { parties: PartyResult[]; colors: Record<string, string>; }

const PowerScatter: React.FC<ScatterProps> = ({ parties, colors }) => {
  const pts = parties.map((p) => ({
    x: Math.round(p.seat_pct * 100),
    y: Math.round(p.shapley_index * 100),
    name: p.name,
    color: p.is_pariah ? '#adb5bd' : (colors[p.name] ?? '#0d6efd'),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" dataKey="x" name="Sièges" unit="%" domain={[0, 100]}
          tick={{ fontSize: 10 }} label={{ value: 'Sièges %', position: 'insideBottom', offset: -10, fontSize: 10 }} />
        <YAxis type="number" dataKey="y" name="Shapley" unit="%" domain={[0, 100]}
          tick={{ fontSize: 10 }} label={{ value: 'Shapley %', angle: -90, position: 'insideLeft', fontSize: 10 }} />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 100, y: 100 }]}
          stroke="#adb5bd" strokeDasharray="4 4" />
        <Tooltip
          content={({ payload }) => {
            if (!payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div style={{ background: '#fff', border: '1px solid #dee2e6', borderRadius: 4, padding: '4px 8px', fontSize: '0.75rem' }}>
                <strong>{d.name}</strong><br />
                Sièges: {d.x}% · Shapley: {d.y}%
              </div>
            );
          }}
        />
        <Scatter data={pts} dataKey="y">
          {pts.map((pt, i) => (
            <Cell key={i} fill={pt.color} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const DEFAULT_PARTIES: PartyInput[] = [
  { name: 'Parti A', seats: 40, pariah: false, color: PALETTE[0] },
  { name: 'Parti B', seats: 35, pariah: false, color: PALETTE[1] },
  { name: 'Parti C', seats: 25, pariah: false, color: PALETTE[2] },
];

const PowerIndicesPanel: React.FC = () => {
  const { t } = useTranslation();

  const [parties,    setParties]    = useState<PartyInput[]>(DEFAULT_PARTIES);
  const [threshold,  setThreshold]  = useState(0);
  const [data,       setData]       = useState<PowerData | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'scatter' | 'hemi' | 'coalitions'>('scatter');
  const [calcShapley, setCalcShapley] = useState(true);
  const [calcBanzhaf, setCalcBanzhaf] = useState(true);

  const colorsMap: Record<string, string> = {};
  parties.forEach((p) => { colorsMap[p.name] = p.color; });

  const totalSeats = parties.reduce((s, p) => s + p.seats, 0);

  const loadPreset = (key: string) => {
    const preset = PRESETS[key];
    if (!preset) return;
    setParties(
      preset.parties.map((p, i) => ({
        ...p, color: PALETTE[i % PALETTE.length],
      }))
    );
    setData(null);
  };

  const addParty = () => {
    const idx = parties.length;
    setParties([...parties, {
      name: `Parti ${String.fromCharCode(65 + idx)}`,
      seats: 10, pariah: false,
      color: PALETTE[idx % PALETTE.length],
    }]);
  };

  const removeParty = (i: number) =>
    setParties(parties.filter((_, j) => j !== i));

  const updateParty = (i: number, field: keyof PartyInput, val: string | number | boolean) =>
    setParties(parties.map((p, j) => j === i ? { ...p, [field]: val } : p));

  const togglePariah = (i: number) => {
    const updated = parties.map((p, j) =>
      j === i ? { ...p, pariah: !p.pariah } : p
    );
    setParties(updated);
    // Auto-recalculate if we already have results
    if (data) runWith(updated, threshold);
  };

  const runWith = async (pts: PartyInput[], thr: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/power-indices')}`, {
        parties: pts.map(({ name, seats, pariah }) => ({ name, seats, pariah })),
        majority_threshold: thr,
        coalition_constraints: [],
        calculate_shapley: calcShapley,
        calculate_banzhaf: calcBanzhaf,
      });
      setData(res.data);
    } catch {
      setError(t('power.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleRun = () => runWith(parties, threshold);

  return (
    <div>
      {/* ── Presets ── */}
      <div className="d-flex flex-wrap gap-2 mb-3" data-testid="presets">
        {Object.entries(PRESETS).map(([key, preset]) => (
          <Button key={key} size="sm" variant="outline-secondary"
            data-testid={`preset-${key}`}
            onClick={() => loadPreset(key)}>
            {preset.label}
          </Button>
        ))}
      </div>

      {/* ── Party editor ── */}
      <div className="mb-3 border rounded p-2" style={{ background: '#f8f9fa' }}
        data-testid="party-editor">
        <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>
          {t('power.partiesTitle')}
          <span className="text-muted ms-2" style={{ fontSize: '0.72rem' }}>
            Total: {totalSeats} {t('power.seats')}
          </span>
        </div>
        {parties.map((p, i) => (
          <Row key={i} className="g-1 mb-1 align-items-center">
            <Col xs={4} md={3}>
              <Form.Control size="sm" value={p.name} placeholder={t('power.partyName')}
                data-testid={`party-name-${i}`}
                onChange={(e) => updateParty(i, 'name', e.target.value)} />
            </Col>
            <Col xs={3} md={2}>
              <Form.Control type="number" size="sm" min={0} max={9999} value={p.seats}
                data-testid={`party-seats-${i}`}
                onChange={(e) => updateParty(i, 'seats', Number(e.target.value))} />
            </Col>
            <Col xs="auto">
              <Form.Check type="switch" id={`pariah-${i}`}
                label={
                  <span style={{ fontSize: '0.72rem', color: p.pariah ? '#dc3545' : '#6c757d' }}>
                    {t('power.pariah')}
                  </span>
                }
                checked={p.pariah}
                data-testid={`pariah-toggle-${i}`}
                onChange={() => togglePariah(i)} />
            </Col>
            <Col xs="auto">
              <div style={{ width: 16, height: 16, borderRadius: '50%',
                background: p.color, border: '1px solid #dee2e6', cursor: 'pointer' }}
                onClick={() => {
                  const idx = PALETTE.indexOf(p.color);
                  updateParty(i, 'color', PALETTE[(idx + 1) % PALETTE.length]);
                }} />
            </Col>
            <Col xs="auto">
              <Button size="sm" variant="link" className="text-danger p-0"
                onClick={() => removeParty(i)}>×</Button>
            </Col>
          </Row>
        ))}
        <Button size="sm" variant="outline-primary" className="mt-1"
          data-testid="add-party-btn" onClick={addParty}>
          + {t('power.addParty')}
        </Button>
      </div>

      {/* ── Controls ── */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">{t('power.threshold')}</Form.Label>
          <Form.Control type="number" size="sm" min={0} value={threshold}
            data-testid="threshold-input"
            placeholder={`Auto (${Math.floor(totalSeats / 2) + 1})`}
            onChange={(e) => setThreshold(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Form.Check inline type="checkbox" id="cb-shapley"
            label={<span style={{ fontSize: '0.8rem' }}>Shapley-Shubik</span>}
            checked={calcShapley}
            data-testid="cb-shapley"
            onChange={(e) => setCalcShapley(e.target.checked)} />
        </Col>
        <Col xs="auto">
          <Form.Check inline type="checkbox" id="cb-banzhaf"
            label={<span style={{ fontSize: '0.8rem' }}>Banzhaf</span>}
            checked={calcBanzhaf}
            data-testid="cb-banzhaf"
            onChange={(e) => setCalcBanzhaf(e.target.checked)} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" size="sm" onClick={handleRun} disabled={loading}
            data-testid="run-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('power.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" data-testid="prompt-alert">{t('power.prompt')}</Alert>
      )}
      {error && <Alert variant="danger" data-testid="error-alert">{error}</Alert>}

      {data && (
        <>
          {/* ── View tabs ── */}
          <div className="d-flex gap-2 mb-3">
            {(['scatter', 'hemi', 'coalitions'] as const).map((v) => (
              <Button key={v} size="sm"
                variant={activeView === v ? 'dark' : 'outline-secondary'}
                data-testid={`view-btn-${v}`}
                onClick={() => setActiveView(v)}>
                {t(`power.view_${v}`)}
              </Button>
            ))}
          </div>

          {/* ── Scatter view ── */}
          {activeView === 'scatter' && (
            <div data-testid="scatter-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('power.scatterTitle')}
              </div>
              <PowerScatter parties={data.parties} colors={colorsMap} />
              <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                {t('power.scatterDesc')}
              </div>
            </div>
          )}

          {/* ── Hemicycle view ── */}
          {activeView === 'hemi' && (
            <div data-testid="hemi-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('power.hemiTitle')}
              </div>
              <PowerHemicycle parties={data.parties} colors={colorsMap} />
            </div>
          )}

          {/* ── Coalitions view ── */}
          {activeView === 'coalitions' && (
            <div data-testid="coalitions-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('power.coalitionsTitle')}
                <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.65rem' }}>
                  {data.viable_coalitions.length}
                </Badge>
              </div>
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {data.viable_coalitions.map((c, i) => (
                  <div key={i}
                    className={`d-flex gap-2 align-items-center px-2 py-1 mb-1 rounded ${c.minimal ? 'border border-success' : ''}`}
                    style={{ background: c.minimal ? '#d1e7dd' : '#f8f9fa', fontSize: '0.75rem' }}
                    data-testid={`coalition-row-${i}`}>
                    {c.parties.map((pn) => (
                      <Badge key={pn} style={{
                        background: colorsMap[pn] ?? '#6c757d', fontSize: '0.65rem',
                      }}>{pn}</Badge>
                    ))}
                    <span className="text-muted ms-auto">{c.seats} {t('power.seats')}</span>
                    {c.minimal && (
                      <Badge bg="success" style={{ fontSize: '0.6rem' }}>minimal</Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Power table ── */}
          <div className="mt-3" data-testid="power-table">
            <Table size="sm" bordered style={{ fontSize: '0.74rem' }}>
              <thead className="table-light">
                <tr>
                  <th>{t('power.colParty')}</th>
                  <th>{t('power.colSeats')}</th>
                  <th>{t('power.colShapley')}</th>
                  <th>{t('power.colBanzhaf')}</th>
                  <th>{t('power.colRatio')}</th>
                  <th>{t('power.colCritical')}</th>
                </tr>
              </thead>
              <tbody>
                {data.parties.map((p) => {
                  const isHighPower = p.power_ratio > 1.5;
                  const isLowPower  = p.power_ratio < 0.5 || p.is_pariah;
                  return (
                    <tr key={p.name}
                      style={{
                        background: p.is_pariah ? '#f8d7da'
                          : isHighPower ? '#d1e7dd'
                          : isLowPower  ? '#fff3cd' : undefined,
                      }}
                      data-testid={`table-row-${p.name}`}>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ width: 8, height: 8, borderRadius: '50%',
                            background: p.is_pariah ? '#adb5bd' : (colorsMap[p.name] ?? '#6c757d'),
                            display: 'inline-block' }} />
                          {p.name}
                          {p.is_pariah && (
                            <Badge bg="danger" style={{ fontSize: '0.55rem' }}>paria</Badge>
                          )}
                        </span>
                      </td>
                      <td>{p.seats} ({Math.round(p.seat_pct * 100)}%)</td>
                      <td style={{ fontWeight: isHighPower ? 700 : undefined,
                        color: p.shapley_index === 0 ? '#adb5bd' : undefined }}>
                        {Math.round(p.shapley_index * 1000) / 10}%
                      </td>
                      <td style={{ color: p.banzhaf_index === 0 ? '#adb5bd' : undefined }}>
                        {Math.round(p.banzhaf_index * 1000) / 10}%
                      </td>
                      <td>
                        <Badge
                          bg={p.is_pariah ? 'secondary'
                            : isHighPower ? 'success'
                            : isLowPower  ? 'warning' : 'light'}
                          text={(!p.is_pariah && !isHighPower && isLowPower) ? 'dark' : undefined}
                          style={{ fontSize: '0.65rem' }}>
                          ×{p.power_ratio.toFixed(2)}
                        </Badge>
                      </td>
                      <td>{p.critical_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </div>

          {/* ── Surprises ── */}
          {data.power_surprises.length > 0 && (
            <div className="mt-2" data-testid="surprises-section">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('power.surprisesTitle')}
              </div>
              {data.power_surprises.map((s, i) => (
                <Alert key={i} variant="warning" className="py-1 mb-1"
                  style={{ fontSize: '0.75rem' }}>
                  ⚡ {s}
                </Alert>
              ))}
            </div>
          )}

          {/* ── Historical examples ── */}
          <div className="mt-3 border rounded p-3" data-testid="examples-section"
            style={{ background: '#f8f9fa', fontSize: '0.75rem' }}>
            <div className="fw-semibold mb-2">{t('power.examplesTitle')}</div>
            <Row className="g-2">
              {[
                { flag: '🇩🇪', country: 'Allemagne 2021', desc: 'AfD : 83 sièges, Banzhaf = 0 (exclu de tout)' },
                { flag: '🇫🇷', country: 'France 2022',    desc: 'RN : 89 sièges, Banzhaf ≈ 0 (cordon sanitaire)' },
                { flag: '🇮🇱', country: 'Israël 2022',    desc: 'Partis ultra-orth. : ~10 sièges, Shapley élevé (pivots)' },
              ].map(({ flag, country, desc }) => (
                <Col key={country} xs={12} md={4}>
                  <div className="border rounded p-2" style={{ background: '#fff' }}>
                    <strong>{flag} {country}</strong>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>{desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note">
            <strong>{t('power.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default PowerIndicesPanel;
