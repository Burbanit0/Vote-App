import React, { useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Card, Col, Form, Row, Spinner,
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PrimaryCandidate {
  name: string;
  ideology_position: number;
}

interface PartyConfig {
  name: string;
  ideology_center: number;
  primary_candidates: PrimaryCandidate[];
  primary_voters_pct: number;
}

interface PrimaryResult {
  party: string;
  winner: string;
  runner_up: string | null;
  distortion: number;
  winner_pos: number;
  party_center: number;
  vote_shares: Record<string, number>;
  num_primary_voters: number;
}

interface PrimaryData {
  primaries: PrimaryResult[];
  general_ballot: string[];
  general_winner: string;
  general_runner_up: string | null;
  general_vote_shares: Record<string, number>;
  median_voter_distance: number;
  without_primaries_winner: string | null;
}

// ── Default config ─────────────────────────────────────────────────────────────

const DEFAULT_PARTIES: PartyConfig[] = [
  {
    name: 'Gauche',
    ideology_center: -0.5,
    primary_voters_pct: 0.25,
    primary_candidates: [
      { name: 'Sophie (modérée)', ideology_position: -0.35 },
      { name: 'Marc (radical)',   ideology_position: -0.75 },
    ],
  },
  {
    name: 'Droite',
    ideology_center: 0.5,
    primary_voters_pct: 0.25,
    primary_candidates: [
      { name: 'Élise (modérée)', ideology_position: 0.35 },
      { name: 'Paul (radical)',  ideology_position: 0.75 },
    ],
  },
  {
    name: 'Centre',
    ideology_center: 0.0,
    primary_voters_pct: 0.15,
    primary_candidates: [
      { name: 'Anna (centre)',  ideology_position: 0.0  },
      { name: 'Tom (libéral)', ideology_position: 0.15 },
    ],
  },
];

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];

function partyColor(idx: number): string {
  return PALETTE[idx % PALETTE.length];
}

// ── Ideological axis SVG ──────────────────────────────────────────────────────

interface IdeologicalAxisProps {
  primaries: PrimaryResult[];
  partyColors: string[];
}

const IdeologicalAxis: React.FC<IdeologicalAxisProps> = ({ primaries, partyColors }) => {
  const W = 480;
  const H = 100;
  const PAD = 32;
  const axisY = 60;
  const lineW = W - 2 * PAD;

  function xPos(v: number): number {
    return PAD + ((v + 1) / 2) * lineW;
  }

  return (
    <svg
      data-testid="ideology-axis"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ maxWidth: 520, display: 'block', margin: '0 auto' }}
    >
      {/* Axis line */}
      <line x1={PAD} y1={axisY} x2={W - PAD} y2={axisY} stroke="#adb5bd" strokeWidth={2} />
      {/* Labels */}
      <text x={PAD}     y={axisY + 16} textAnchor="middle" fontSize={10} fill="#6c757d">−1</text>
      <text x={W / 2}   y={axisY + 16} textAnchor="middle" fontSize={10} fill="#6c757d">0</text>
      <text x={W - PAD} y={axisY + 16} textAnchor="middle" fontSize={10} fill="#6c757d">+1</text>

      {/* Left / Right labels */}
      <text x={PAD}     y={axisY - 18} textAnchor="start"  fontSize={9} fill="#6c757d">← Gauche / Left</text>
      <text x={W - PAD} y={axisY - 18} textAnchor="end"    fontSize={9} fill="#6c757d">Droite / Right →</text>

      {/* Zero tick */}
      <line x1={W / 2} y1={axisY - 6} x2={W / 2} y2={axisY + 6} stroke="#ced4da" strokeWidth={1} />

      {primaries.map((p, i) => {
        const color  = partyColors[i];
        const cx     = xPos(p.party_center);
        const wx     = xPos(p.winner_pos);
        const drifted = Math.abs(p.winner_pos - p.party_center) > 0.01;

        return (
          <g key={p.party}>
            {/* Party centre (grey, hollow circle) */}
            <circle cx={cx} cy={axisY} r={6} fill="#fff" stroke="#adb5bd" strokeWidth={1.5}>
              <title>{p.party} — centre: {p.party_center.toFixed(2)}</title>
            </circle>

            {/* Arrow from centre to winner if drifted */}
            {drifted && (
              <line
                x1={cx} y1={axisY}
                x2={wx - (wx > cx ? 8 : -8)} y2={axisY}
                stroke={color} strokeWidth={1.5} strokeDasharray="3 2"
                markerEnd="url(#arrowhead)"
              />
            )}

            {/* Winner (filled circle) */}
            <circle cx={wx} cy={axisY} r={7} fill={color} stroke="#fff" strokeWidth={1.5}>
              <title>{p.winner} — pos: {p.winner_pos.toFixed(2)}</title>
            </circle>

            {/* Label above */}
            <text
              x={wx} y={axisY - 14}
              textAnchor="middle" fontSize={9} fill={color} fontWeight={600}
            >
              {p.winner.split(' ')[0]}
            </text>
          </g>
        );
      })}

      {/* SVG arrowhead marker */}
      <defs>
        <marker id="arrowhead" markerWidth={6} markerHeight={6} refX={3} refY={3} orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="#adb5bd" />
        </marker>
      </defs>
    </svg>
  );
};

// ── Mini bar chart for one party's primary ────────────────────────────────────

const PrimaryBar: React.FC<{ result: PrimaryResult; color: string }> = ({ result, color }) => {
  const chartData = Object.entries(result.vote_shares).map(([name, pct]) => ({
    name: name.split(' ')[0],
    pct:  Math.round(pct * 100),
    isWinner: name === result.winner,
  }));

  return (
    <div style={{ height: 110 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} unit="%" />
          <Tooltip formatter={(v: number) => `${v}%`} />
          <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.isWinner ? color : `${color}55`} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ── Party config editor ───────────────────────────────────────────────────────

interface PartyEditorProps {
  parties: PartyConfig[];
  onChange: (updated: PartyConfig[]) => void;
  t: (k: string) => string;
}

const PartyEditor: React.FC<PartyEditorProps> = ({ parties, onChange, t }) => {
  function updateParty(idx: number, patch: Partial<PartyConfig>) {
    onChange(parties.map((p, i) => i === idx ? { ...p, ...patch } : p));
  }

  function updateCandidate(pIdx: number, cIdx: number, patch: Partial<PrimaryCandidate>) {
    const updated = parties.map((p, i) => {
      if (i !== pIdx) return p;
      return {
        ...p,
        primary_candidates: p.primary_candidates.map((c, j) =>
          j === cIdx ? { ...c, ...patch } : c
        ),
      };
    });
    onChange(updated);
  }

  return (
    <div>
      {parties.map((party, pIdx) => (
        <Card key={pIdx} className="mb-2" style={{ fontSize: '0.78rem', borderLeft: `4px solid ${partyColor(pIdx)}` }}>
          <Card.Body className="p-2">
            <div className="d-flex align-items-center gap-2 mb-1">
              <div style={{ width: 10, height: 10, borderRadius: 2, background: partyColor(pIdx), flexShrink: 0 }} />
              <strong>{party.name}</strong>
              <span className="text-muted ms-auto">
                {t('primary.center')}: {party.ideology_center.toFixed(2)}
              </span>
            </div>
            <Form.Range
              min={-1} max={1} step={0.05} value={party.ideology_center}
              onChange={(e) => updateParty(pIdx, { ideology_center: Number(e.target.value) })}
              className="mb-1"
              style={{ minHeight: 44 }}
            />
            <div className="text-muted mb-1" style={{ fontSize: '0.72rem' }}>
              {t('primary.primaryVotersPct')}: {Math.round(party.primary_voters_pct * 100)}%
              <Form.Range
                min={0.05} max={0.6} step={0.05} value={party.primary_voters_pct}
                onChange={(e) => updateParty(pIdx, { primary_voters_pct: Number(e.target.value) })}
                style={{ minHeight: 44 }}
              />
            </div>
            <div className="ps-2">
              {party.primary_candidates.map((c, cIdx) => (
                <div key={cIdx} className="d-flex align-items-center gap-1 mb-1">
                  <span style={{ minWidth: 80, fontSize: '0.72rem' }}>{c.name.split(' ')[0]}</span>
                  <Form.Range
                    min={-1} max={1} step={0.05} value={c.ideology_position}
                    onChange={(e) => updateCandidate(pIdx, cIdx, { ideology_position: Number(e.target.value) })}
                    style={{ flex: 1 }}
                  />
                  <span style={{ minWidth: 32, fontSize: '0.7rem', textAlign: 'right' }}>
                    {c.ideology_position >= 0 ? '+' : ''}{c.ideology_position.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      ))}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const PrimarySimulator: React.FC = () => {
  const { t } = useTranslation();

  const [parties, setParties] = useState<PartyConfig[]>(DEFAULT_PARTIES);
  const [primaryMethod, setPrimaryMethod]   = useState('plurality');
  const [generalMethod, setGeneralMethod]   = useState('plurality');
  const [numVoters, setNumVoters]           = useState(500);
  const [data, setData]     = useState<PrimaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/primary')}`, {
        parties,
        general_num_voters: numVoters,
        general_ideology:   'random',
        primary_method:     primaryMethod,
        general_method:     generalMethod,
        seed:               42,
      });
      setData(res.data);
    } catch {
      setError(t('primary.error'));
    } finally {
      setLoading(false);
    }
  }

  const partyColors = parties.map((_, i) => partyColor(i));
  const maxDistortion = data
    ? Math.max(...data.primaries.map((p) => p.distortion), 0.001)
    : 1;
  const anyDrift = data ? data.primaries.some((p) => p.distortion > 0.1) : false;
  const primaryChanged = data && data.general_winner !== data.without_primaries_winner;

  return (
    <div>
      <Row className="g-3">
        {/* ── Left panel: config ── */}
        <Col xs={12} md={4}>
          <div className="mb-2" style={{ fontSize: '0.8rem', fontWeight: 600 }}>
            {t('primary.partyConfig')}
          </div>
          <PartyEditor parties={parties} onChange={setParties} t={t} />

          <div className="mt-3" style={{ fontSize: '0.8rem' }}>
            <Form.Label className="mb-0">{t('primary.primaryMethod')}</Form.Label>
            <Form.Select size="sm" value={primaryMethod}
              onChange={(e) => setPrimaryMethod(e.target.value)} className="mb-2">
              <option value="plurality">{t('primary.methodPlurality')}</option>
              <option value="irv">{t('primary.methodIrv')}</option>
              <option value="approval">{t('primary.methodApproval')}</option>
            </Form.Select>

            <Form.Label className="mb-0">{t('primary.generalMethod')}</Form.Label>
            <Form.Select size="sm" value={generalMethod}
              onChange={(e) => setGeneralMethod(e.target.value)} className="mb-2">
              <option value="plurality">{t('primary.methodPlurality')}</option>
              <option value="irv">{t('primary.methodIrv')}</option>
              <option value="approval">{t('primary.methodApproval')}</option>
            </Form.Select>

            <Form.Label className="mb-0">
              {t('primary.numVoters')}: <strong>{numVoters}</strong>
            </Form.Label>
            <Form.Range min={100} max={1000} step={100} value={numVoters}
              onChange={(e) => setNumVoters(Number(e.target.value))} />
          </div>

          <Button variant="primary" className="w-100 mt-2" onClick={run} disabled={loading}>
            {loading
              ? <><Spinner size="sm" className="me-2" />{t('primary.simulating')}</>
              : `🗳 ${t('primary.run')}`}
          </Button>
          {error && <Alert variant="danger" className="mt-2">{error}</Alert>}
        </Col>

        {/* ── Right panel: results ── */}
        <Col xs={12} md={8}>
          {!data && !loading && (
            <Alert variant="info">{t('primary.prompt')}</Alert>
          )}

          {data && (
            <>
              {/* Summary badges */}
              <div className="d-flex flex-wrap gap-2 mb-3">
                <Badge bg="primary" data-testid="general-winner-badge">
                  {t('primary.generalWinner')}: {data.general_winner}
                </Badge>
                {data.without_primaries_winner && (
                  <Badge bg={primaryChanged ? 'warning' : 'success'} text={primaryChanged ? 'dark' : undefined}
                    data-testid="no-primary-winner-badge">
                    {t('primary.withoutPrimaries')}: {data.without_primaries_winner}
                  </Badge>
                )}
                <Badge bg="secondary">
                  {t('primary.medianDistance')}: {data.median_voter_distance.toFixed(3)}
                </Badge>
                {anyDrift && (
                  <Badge bg="danger" data-testid="drift-badge">
                    ⚠ {t('primary.driftDetected')}
                  </Badge>
                )}
              </div>

              {/* Pedagogical message */}
              <Alert
                variant={primaryChanged ? 'warning' : 'success'}
                className="py-2 mb-3"
                style={{ fontSize: '0.84rem' }}
              >
                {primaryChanged
                  ? t('primary.pedagogicalChanged', {
                      winner:       data.general_winner,
                      noWinner:     data.without_primaries_winner ?? '?',
                      medianDist:   data.median_voter_distance.toFixed(3),
                    })
                  : t('primary.pedagogicalSame', { winner: data.general_winner })}
              </Alert>

              {/* Phase 1: Primaries */}
              <div className="mb-1" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {t('primary.phase1')}
              </div>
              <Row className="g-2 mb-3" data-testid="primaries-section">
                {data.primaries.map((p, i) => (
                  <Col key={p.party} xs={12} sm={6} lg={4}>
                    <Card className="h-100" style={{ fontSize: '0.78rem', borderTop: `3px solid ${partyColors[i]}` }}>
                      <Card.Body className="p-2">
                        <div className="d-flex align-items-center gap-1 mb-1">
                          <strong>{p.party}</strong>
                          {p.distortion > 0.1 && (
                            <Badge bg="warning" text="dark" style={{ fontSize: '0.65rem' }}
                              data-testid={`drift-badge-${p.party}`}>
                              +{p.distortion.toFixed(2)}
                            </Badge>
                          )}
                        </div>
                        <div className="text-muted mb-1">
                          ✓ {p.winner}
                          {p.runner_up && <span className="ms-2 text-muted">({p.runner_up})</span>}
                        </div>
                        <PrimaryBar result={p} color={partyColors[i]} />
                        {/* Distortion bar */}
                        <div style={{ height: 6, background: '#e9ecef', borderRadius: 3, marginTop: 4 }}>
                          <div style={{
                            width: `${Math.min(100, (p.distortion / maxDistortion) * 100)}%`,
                            height: '100%',
                            background: p.distortion > 0.1 ? '#dc3545' : '#6c757d',
                            borderRadius: 3,
                            transition: 'width 0.4s',
                          }} />
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.7rem', marginTop: 2 }}>
                          {t('primary.distortion')}: {p.distortion.toFixed(3)}
                        </div>
                      </Card.Body>
                    </Card>
                  </Col>
                ))}
              </Row>

              {/* Ideological axis */}
              <div className="mb-1" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {t('primary.ideologyAxis')}
              </div>
              <div className="border rounded p-2 mb-3">
                <IdeologicalAxis primaries={data.primaries} partyColors={partyColors} />
                <div className="d-flex gap-3 justify-content-center mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
                  <span>○ {t('primary.partyCenter')} &nbsp; ● {t('primary.selectedCandidate')}</span>
                </div>
              </div>

              {/* Phase 2: General election */}
              <div className="mb-1" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {t('primary.phase2')}
              </div>
              <div className="border rounded p-2" data-testid="general-section">
                <div style={{ height: 160 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.general_ballot.map((name) => ({
                        name: name.split(' ')[0],
                        pct:  Math.round((data.general_vote_shares[name] ?? 0) * 100),
                        isWinner: name === data.general_winner,
                        color: partyColors[data.primaries.findIndex((p) => p.winner === name)],
                      }))}
                      margin={{ top: 8, right: 8, bottom: 4, left: -10 }}
                    >
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
                      <Tooltip formatter={(v: number) => `${v}%`} />
                      <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                        {data.general_ballot.map((name, i) => {
                          const pIdx = data.primaries.findIndex((p) => p.winner === name);
                          return (
                            <Cell
                              key={i}
                              fill={pIdx >= 0 ? partyColors[pIdx] : '#adb5bd'}
                              opacity={name === data.general_winner ? 1 : 0.5}
                            />
                          );
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default PrimarySimulator;
