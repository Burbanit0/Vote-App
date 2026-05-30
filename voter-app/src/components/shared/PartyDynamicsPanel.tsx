/**
 * PartyDynamicsPanel — simulates multi-election party system evolution.
 * Shows Duverger's Law: FPTP → bipartism; PR → multipartism.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  ReferenceLine, Legend, ResponsiveContainer,
} from 'recharts';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';
const ANIM_MS = 800;

// ── Types ─────────────────────────────────────────────────────────────────────

interface PartySnap {
  name:     string;
  x:        number;
  y:        number;
  vote_pct: number;
  seats:    number;
  survived: boolean;
}

interface ElectionRecord {
  election_n:        number;
  active_parties:    number;
  parties:           PartySnap[];
  effective_parties: number;
  winner:            string;
  new_entrants:      string[];
  eliminated:        string[];
}

interface DynamicsData {
  elections:               ElectionRecord[];
  final_system:            string;
  effective_parties_curve: number[];
  duverger_confirmed:      boolean;
  convergence_speed:       number | null;
  ideology_drift:          { party: string; initial_x: number; final_x: number }[];
  pedagogical_note:        string;
}

// ── Presets ───────────────────────────────────────────────────────────────────

const PRESETS: Record<string, { label: string; parties: { name: string; x: number; y: number; support_pct: number }[] }> = {
  default: {
    label: '5 partis génériques',
    parties: [
      { name: 'A', x: -0.8, y: 0, support_pct: 0.10 },
      { name: 'B', x: -0.3, y: 0, support_pct: 0.25 },
      { name: 'C', x:  0.1, y: 0, support_pct: 0.30 },
      { name: 'D', x:  0.5, y: 0, support_pct: 0.25 },
      { name: 'E', x:  0.9, y: 0, support_pct: 0.10 },
    ],
  },
  france: {
    label: 'France (LFI/PS/LREM/LR/RN)',
    parties: [
      { name: 'LFI',  x: -0.75, y:  0.1, support_pct: 0.15 },
      { name: 'PS',   x: -0.40, y:  0.0, support_pct: 0.08 },
      { name: 'LREM', x:  0.05, y:  0.0, support_pct: 0.30 },
      { name: 'LR',   x:  0.45, y:  0.0, support_pct: 0.10 },
      { name: 'RN',   x:  0.75, y: -0.1, support_pct: 0.28 },
    ],
  },
  usa: {
    label: 'USA (Dem/Rep)',
    parties: [
      { name: 'Democrats',   x: -0.4, y: 0, support_pct: 0.50 },
      { name: 'Republicans', x:  0.4, y: 0, support_pct: 0.50 },
    ],
  },
};

// ── Palette ───────────────────────────────────────────────────────────────────

const PARTY_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#9b59b6',
  '#e67e22', '#e83e8c', '#17a2b8', '#dc3545', '#6c757d', '#198754',
];
function partyColor(name: string, allNames: string[]): string {
  const i = allNames.indexOf(name);
  return PARTY_COLORS[i >= 0 ? i % PARTY_COLORS.length : 0];
}

// ── Ideology map SVG ──────────────────────────────────────────────────────────

const SVG_W = 480, SVG_H = 260, PAD = 40;
function px(x: number) { return PAD + ((x + 1) / 2) * (SVG_W - 2 * PAD); }
function py(y: number) { return SVG_H / 2 - y * (SVG_H / 2 - PAD); }

interface IdeologyMapProps {
  elections:    ElectionRecord[];
  currentIdx:   number;
  allPartyNames: string[];
}

const IdeologyMap: React.FC<IdeologyMapProps> = ({ elections, currentIdx, allPartyNames }) => {
  if (!elections.length) return null;
  const current = elections[currentIdx];
  const prev    = currentIdx > 0 ? elections[currentIdx - 1] : null;

  return (
    <svg data-testid="ideology-map-svg" width="100%" viewBox={`0 0 ${SVG_W} ${SVG_H}`}>
      {/* Axes */}
      <line x1={PAD} y1={SVG_H/2} x2={SVG_W-PAD} y2={SVG_H/2} stroke="#dee2e6" strokeWidth={1.5} />
      <text x={PAD} y={SVG_H/2+14} textAnchor="middle" style={{ fontSize: 9, fill: '#adb5bd' }}>G</text>
      <text x={SVG_W-PAD} y={SVG_H/2+14} textAnchor="middle" style={{ fontSize: 9, fill: '#adb5bd' }}>D</text>
      <text x={SVG_W/2} y={12} textAnchor="middle" style={{ fontSize: 10, fill: '#6c757d' }}>
        Élection {current.election_n}
      </text>

      {/* Trajectories */}
      {allPartyNames.map((name) => {
        const pts = elections.slice(0, currentIdx + 1)
          .map((e) => e.parties.find((p) => p.name === name))
          .filter(Boolean) as PartySnap[];
        if (pts.length < 2) return null;
        const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${px(p.x)},${py(p.y)}`).join(' ');
        return (
          <path key={name} d={d} fill="none"
            stroke={partyColor(name, allPartyNames)} strokeWidth={0.8}
            strokeDasharray="3 2" opacity={0.5} />
        );
      })}

      {/* Party circles */}
      {current.parties.map((p) => {
        const r  = Math.max(5, Math.sqrt(p.vote_pct) * 3);
        const cx = px(p.x);
        const cy = py(p.y);
        const color = partyColor(p.name, allPartyNames);
        return (
          <g key={p.name}>
            {/* New entrant pulse */}
            {current.new_entrants.includes(p.name) && (
              <circle cx={cx} cy={cy} r={r + 6} fill="none"
                stroke={color} strokeWidth={1.5} strokeDasharray="4 2" opacity={0.6} />
            )}
            <circle cx={cx} cy={cy} r={r}
              fill={p.survived ? color : '#adb5bd'}
              opacity={p.survived ? 0.9 : 0.4} />
            <text x={cx} y={cy - r - 3} textAnchor="middle"
              style={{ fontSize: 9, fill: color, fontWeight: 600 }}>
              {p.name} {p.vote_pct.toFixed(0)}%
            </text>
          </g>
        );
      })}

      {/* Eliminated (faded) from previous */}
      {prev && prev.parties
        .filter((p) => !current.parties.some((cp) => cp.name === p.name))
        .map((p) => (
          <text key={p.name} x={px(p.x)} y={py(p.y) + 4} textAnchor="middle"
            style={{ fontSize: 9, fill: '#dc3545' }}>✕ {p.name}</text>
        ))}
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

interface Props {
  onDataLoaded?: (data: DynamicsData) => void;
}

const PartyDynamicsPanel: React.FC<Props> = ({ onDataLoaded }) => {
  const { t } = useTranslation();

  const [method,       setMethod]       = useState('plurality');
  const [numElections, setNumElections] = useState(15);
  const [survThr,      setSurvThr]      = useState(0.05);
  const [hotelling,    setHotelling]    = useState(0.10);
  const [emerge,       setEmerge]       = useState(0.0);
  const [tactical,     setTactical]     = useState(true);
  const [preset,       setPreset]       = useState('default');
  const [parties,      setParties]      = useState(PRESETS.default.parties);

  const [data,         setData]         = useState<DynamicsData | null>(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [electionIdx,  setElectionIdx]  = useState(0);
  const [playing,      setPlaying]      = useState(false);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const applyPreset = (key: string) => {
    setPreset(key);
    setParties(PRESETS[key]?.parties ?? PRESETS.default.parties);
  };

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPlaying(false);
    setElectionIdx(0);
    try {
      const res = await axios.post(`${API}${apiPath('election/party-dynamics')}`, {
        initial_parties:       parties,
        num_voters:            300,
        ideology:              'random',
        seed:                  42,
        num_elections:         numElections,
        method,
        survival_threshold:    survThr,
        emergence_probability: emerge,
        hotelling_adaptation:  hotelling,
        tactical_voting:       tactical,
      });
      setData(res.data);
      onDataLoaded?.(res.data);
    } catch {
      setError(t('partyDyn.error'));
    } finally {
      setLoading(false);
    }
  }, [parties, numElections, method, survThr, emerge, hotelling, tactical, t, onDataLoaded]);

  // Animation
  useEffect(() => {
    if (animRef.current) clearInterval(animRef.current);
    if (!playing || !data) return;
    animRef.current = setInterval(() => {
      setElectionIdx((prev) => {
        if (prev >= data.elections.length - 1) {
          setPlaying(false);
          clearInterval(animRef.current!);
          return prev;
        }
        return prev + 1;
      });
    }, ANIM_MS);
    return () => { if (animRef.current) clearInterval(animRef.current); };
  }, [playing, data]);

  const allPartyNames = data
    ? Array.from(new Set(data.elections.flatMap((e) => e.parties.map((p) => p.name))))
    : [];

  const nEffData = data?.effective_parties_curve.map((v, i) => ({
    election: i + 1, n_eff: Math.round(v * 100) / 100,
  })) ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('partyDyn.preset')}</Form.Label>
          <Form.Select size="sm" value={preset} data-testid="preset-select"
            onChange={(e) => applyPreset(e.target.value)}>
            {Object.entries(PRESETS).map(([k, p]) => (
              <option key={k} value={k}>{p.label}</option>
            ))}
          </Form.Select>
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('partyDyn.method')}</Form.Label>
          <Form.Select size="sm" value={method} data-testid="method-select"
            onChange={(e) => setMethod(e.target.value)}>
            <option value="plurality">Plurality (FPTP)</option>
            <option value="irv">Vote alternatif (IRV)</option>
            <option value="borda">Borda</option>
            <option value="proportional">Proportionnelle</option>
          </Form.Select>
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">
            {t('partyDyn.numElections')}: <strong>{numElections}</strong>
          </Form.Label>
          <Form.Range min={3} max={30} step={1} value={numElections}
            data-testid="num-elections-slider"
            onChange={(e) => setNumElections(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">
            {t('partyDyn.survivalThr')}: <strong>{Math.round(survThr * 100)}%</strong>
          </Form.Label>
          <Form.Range min={0.01} max={0.15} step={0.01} value={survThr}
            data-testid="survival-slider"
            onChange={(e) => setSurvThr(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={2}>
          <Form.Check type="switch" id="tactical-switch" label={t('partyDyn.tacticalVoting')}
            checked={tactical}
            data-testid="tactical-switch"
            onChange={(e) => setTactical(e.target.checked)} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading} data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('partyDyn.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('partyDyn.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg={data.final_system === 'bipartite' ? 'danger' : 'primary'}
              data-testid="final-system-badge">
              {t('partyDyn.finalSystem')}: {data.final_system}
            </Badge>
            <Badge bg={data.duverger_confirmed ? 'danger' : 'secondary'}
              data-testid="duverger-badge">
              {data.duverger_confirmed ? t('partyDyn.duvergerConfirmed') : t('partyDyn.duvergerNotConfirmed')}
            </Badge>
            {data.convergence_speed != null && (
              <Badge bg="warning" text="dark" data-testid="convergence-badge">
                {t('partyDyn.convergence')}: {data.convergence_speed} {t('partyDyn.elections')}
              </Badge>
            )}
          </div>

          {/* Animation controls */}
          <div className="d-flex align-items-center gap-2 mb-2">
            <Button size="sm" variant="outline-secondary"
              onClick={() => { setElectionIdx(0); setPlaying(false); }}>⏮</Button>
            <Button size="sm" variant={playing ? 'warning' : 'success'}
              data-testid="play-btn"
              onClick={() => {
                if (electionIdx >= data.elections.length - 1) setElectionIdx(0);
                setPlaying((p) => !p);
              }}>
              {playing ? '⏸' : '▶'}
            </Button>
            <Form.Range
              data-testid="election-slider"
              min={0} max={data.elections.length - 1} step={1}
              value={electionIdx}
              onChange={(e) => { setElectionIdx(Number(e.target.value)); setPlaying(false); }}
              style={{ maxWidth: 200 }}
            />
            <span style={{ fontSize: '0.78rem', color: '#6c757d' }}>
              {t('partyDyn.electionN')} {electionIdx + 1} / {data.elections.length}
            </span>
          </div>

          {/* Ideology map */}
          <div className="border rounded mb-3" style={{ background: '#f8f9fa', overflow: 'hidden' }}>
            <IdeologyMap
              elections={data.elections}
              currentIdx={electionIdx}
              allPartyNames={allPartyNames}
            />
          </div>

          {/* N_eff chart */}
          <div data-testid="n-eff-chart" className="mb-4">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('partyDyn.nEffTitle')}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={nEffData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="election" label={{ value: t('partyDyn.electionN'), position: 'insideBottom', offset: -2, fontSize: 10 }} />
                <YAxis domain={[1, 'auto']} tick={{ fontSize: 10 }} />
                <Tooltip />
                <ReferenceLine y={2.0} stroke="#dc3545" strokeDasharray="4 2"
                  label={{ value: 'Bipartisme', fill: '#dc3545', fontSize: 9 }} />
                <Line type="monotone" dataKey="n_eff"
                  name={t('partyDyn.effectiveParties')}
                  stroke="#005CAB" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('partyDyn.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default PartyDynamicsPanel;
