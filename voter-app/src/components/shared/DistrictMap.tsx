import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import { useElection } from '../../context/ElectionContext';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';

// ── Types ─────────────────────────────────────────────────────────────────────

interface DistrictResult {
  id: number;
  ideology_center: number;
  winner_fptp: string;
  vote_shares: Record<string, number>;
}

interface DistrictData {
  districts: DistrictResult[];
  parliament_fptp: Record<string, number>;
  parliament_proportional: Record<string, number>;
  national_vote_share: Record<string, number>;
  distortion: number;
  condorcet_winner_national: string | null;
  fptp_winner: string;
  proportional_winner: string;
  num_districts: number;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = [
  '#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22',
];

function candidateColor(name: string, names: string[]): string {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── SVG Hémicycle ─────────────────────────────────────────────────────────────

interface HémicycleProps {
  seats: Record<string, number>;
  candidateNames: string[];
  totalSeats: number;
  label: string;
}

const Hémicycle: React.FC<HémicycleProps> = ({ seats, candidateNames, totalSeats, label }) => {
  const W = 260;
  const H = 145;
  const cx = W / 2;
  const cy = H - 8;
  const rInner = 45;
  const rOuter = 115;

  const parties = candidateNames.filter((n) => (seats[n] ?? 0) > 0);
  const total = totalSeats || 1;

  const segments: { name: string; startAngle: number; endAngle: number }[] = [];
  let cumAngle = Math.PI;
  for (const name of parties) {
    const span = ((seats[name] ?? 0) / total) * Math.PI;
    segments.push({ name, startAngle: cumAngle, endAngle: cumAngle + span });
    cumAngle += span;
  }

  function polar(r: number, a: number): [number, number] {
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  }

  function arcPath(r1: number, r2: number, a1: number, a2: number): string {
    const [x1, y1] = polar(r1, a1);
    const [x2, y2] = polar(r2, a1);
    const [x3, y3] = polar(r2, a2);
    const [x4, y4] = polar(r1, a2);
    const la = a2 - a1 > Math.PI ? 1 : 0;
    return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
  }

  return (
    <div className="text-center">
      <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 2 }}>{label}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 280 }} role="img" aria-label={label}>
        {segments.map(({ name, startAngle, endAngle }) => (
          <path
            key={name}
            d={arcPath(rInner, rOuter, startAngle, endAngle)}
            fill={candidateColor(name, candidateNames)}
            stroke="#fff"
            strokeWidth={1.5}
          >
            <title>{name}: {seats[name]}</title>
          </path>
        ))}
        <line
          x1={polar(rInner - 4, Math.PI / 2)[0]} y1={polar(rInner - 4, Math.PI / 2)[1]}
          x2={polar(rOuter + 4, Math.PI / 2)[0]} y2={polar(rOuter + 4, Math.PI / 2)[1]}
          stroke="#dc3545" strokeWidth={1.5} strokeDasharray="3 2"
        />
      </svg>
      <div className="d-flex flex-wrap gap-1 justify-content-center mt-1">
        {candidateNames.filter((n) => (seats[n] ?? 0) > 0).map((name) => (
          <span key={name} style={{ fontSize: '0.72rem' }}>
            <span
              style={{
                display: 'inline-block', width: 10, height: 10,
                background: candidateColor(name, candidateNames), borderRadius: 2, marginRight: 3,
              }}
            />
            {name} ({seats[name]})
          </span>
        ))}
      </div>
    </div>
  );
};

// ── District grid ─────────────────────────────────────────────────────────────

interface DistrictGridProps {
  districts: DistrictResult[];
  candidateNames: string[];
  revealedCount: number;
}

const DistrictGrid: React.FC<DistrictGridProps> = ({ districts, candidateNames, revealedCount }) => {
  const n       = districts.length;
  // On narrow viewports the SVG scales down via width="100%"; we cap columns
  // to 5 on mobile by checking if window exists (SSR-safe)
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const CELL    = isMobile ? 48 : 32;
  const cols    = isMobile ? Math.min(5, Math.ceil(Math.sqrt(n))) : Math.min(10, Math.ceil(Math.sqrt(n * 2)));

  return (
    <svg
      data-testid="district-grid"
      viewBox={`0 0 ${cols * CELL} ${Math.ceil(n / cols) * CELL}`}
      width="100%"
      style={{ maxWidth: 480, display: 'block', margin: '0 auto' }}
    >
      {districts.map((d, idx) => {
        const col = idx % cols;
        const row = Math.floor(idx / cols);
        const revealed = idx < revealedCount;
        const winner = d.winner_fptp;
        const color = revealed ? candidateColor(winner, candidateNames) : '#dee2e6';
        // ideology gradient tint: left-leaning = slight blue, right = slight red
        const ideoBg = d.ideology_center < 0 ? '#e8f0ff' : d.ideology_center > 0 ? '#fff0e8' : '#f8f9fa';

        const topShare = Math.max(...Object.values(d.vote_shares));
        const tooltip = Object.entries(d.vote_shares)
          .sort(([, a], [, b]) => b - a)
          .map(([n, s]) => `${n} ${Math.round(s * 100)}%`)
          .join(' | ');

        return (
          <g key={d.id}>
            <rect
              x={col * CELL + 1}
              y={row * CELL + 1}
              width={CELL - 2}
              height={CELL - 2}
              rx={4}
              fill={revealed ? color : ideoBg}
              stroke={revealed ? '#fff' : '#ced4da'}
              strokeWidth={1}
              opacity={revealed ? 0.85 + topShare * 0.15 : 1}
              style={{ transition: 'fill 0.4s ease, opacity 0.3s' }}
            >
              <title>{`District ${d.id + 1} — ${tooltip}`}</title>
            </rect>
            {revealed && (
              <text
                x={col * CELL + CELL / 2}
                y={row * CELL + CELL / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={9}
                fill="#fff"
                fontWeight={600}
                style={{ pointerEvents: 'none' }}
              >
                {winner?.[0] ?? '?'}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const DistrictMap: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [data, setData] = useState<DistrictData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revealedCount, setRevealedCount] = useState(0);

  const [numDistricts, setNumDistricts] = useState(20);
  const [votersPerDistrict, setVotersPerDistrict] = useState(100);
  const [ideologyVariance, setIdeologyVariance] = useState(0.4);

  const animRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const candidateNames = useMemo(() => config.candidates.map((c) => c.name), [config.candidates]);

  const runAnimation = useCallback((total: number) => {
    setRevealedCount(0);
    let i = 0;
    function step() {
      i++;
      setRevealedCount(i);
      if (i < total) {
        animRef.current = setTimeout(step, 60);
      }
    }
    animRef.current = setTimeout(step, 60);
  }, []);

  useEffect(() => () => { if (animRef.current) clearTimeout(animRef.current); }, []);

  async function run() {
    if (animRef.current) clearTimeout(animRef.current);
    setLoading(true);
    setError(null);
    setRevealedCount(0);
    try {
      const res = await axios.post(`${API}${apiPath('election/districts')}`, {
        candidates:                  config.candidates,
        num_districts:               numDistricts,
        voters_per_district:         votersPerDistrict,
        district_ideology_variance:  ideologyVariance,
        seed:                        config.seed,
      });
      setData(res.data);
      runAnimation(res.data.num_districts);
    } catch {
      setError(t('districts.error'));
    } finally {
      setLoading(false);
    }
  }

  const winnerChanged = data && data.fptp_winner !== data.proportional_winner;
  const distortionPct = data ? Math.round(data.distortion * 100) : 0;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 align-items-end mb-3">
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('districts.numDistricts')}: <strong>{numDistricts}</strong>
          </Form.Label>
          <Form.Range min={5} max={50} step={5} value={numDistricts}
            onChange={(e) => setNumDistricts(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('districts.votersPerDistrict')}: <strong>{votersPerDistrict}</strong>
          </Form.Label>
          <Form.Range min={50} max={300} step={50} value={votersPerDistrict}
            onChange={(e) => setVotersPerDistrict(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('districts.ideologyVariance')}: <strong>{ideologyVariance.toFixed(1)}</strong>
          </Form.Label>
          <Form.Range min={0} max={1} step={0.1} value={ideologyVariance}
            onChange={(e) => setIdeologyVariance(Number(e.target.value))} />
        </Col>
        <Col xs={12} className="d-flex gap-2">
          <Button variant="primary" onClick={run} disabled={loading}>
            {loading
              ? <><Spinner size="sm" className="me-2" />{t('districts.computing')}</>
              : `🗺 ${t('districts.run')}`}
          </Button>
          {data && (
            <Button variant="outline-secondary" size="sm" onClick={() => runAnimation(data.num_districts)}>
              ▶ {t('districts.replay')}
            </Button>
          )}
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}

      {!data && !loading && (
        <Alert variant="info">{t('districts.prompt')}</Alert>
      )}

      {data && (
        <>
          {/* Summary badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg="primary">FPTP: {data.fptp_winner}</Badge>
            <Badge bg={winnerChanged ? 'warning' : 'success'} text={winnerChanged ? 'dark' : undefined}>
              PR: {data.proportional_winner}
            </Badge>
            <Badge bg={distortionPct > 10 ? 'danger' : 'secondary'} data-testid="distortion-badge">
              {t('districts.distortion')}: {distortionPct > 0 ? '+' : ''}{distortionPct}pts
            </Badge>
            {data.condorcet_winner_national && (
              <Badge bg="info">Condorcet: {data.condorcet_winner_national} ✓</Badge>
            )}
          </div>

          {/* Pedagogical message */}
          <Alert
            variant={winnerChanged ? 'warning' : 'success'}
            className="py-2 mb-3"
            style={{ fontSize: '0.84rem' }}
          >
            {winnerChanged
              ? t('districts.pedagogicalDivergence', {
                  fptpWinner:         data.fptp_winner,
                  fptpSeatPct:        Math.round((data.parliament_fptp[data.fptp_winner] ?? 0) / data.num_districts * 100),
                  fptpVotePct:        Math.round((data.national_vote_share[data.fptp_winner] ?? 0) * 100),
                  proportionalWinner: data.proportional_winner,
                })
              : t('districts.pedagogicalConsensus', { winner: data.fptp_winner })}
          </Alert>

          {/* District grid */}
          <div className="mb-4">
            <div className="text-center small text-muted mb-2">{t('districts.gridLabel')}</div>
            <DistrictGrid
              districts={data.districts}
              candidateNames={candidateNames}
              revealedCount={revealedCount}
            />
            {/* Color legend */}
            <div className="d-flex flex-wrap gap-3 justify-content-center mt-2">
              {candidateNames.map((name) => (
                <div key={name} className="d-flex align-items-center gap-1" style={{ fontSize: '0.78rem' }}>
                  <div style={{
                    width: 14, height: 14, borderRadius: 3,
                    background: candidateColor(name, candidateNames),
                  }} />
                  {name} — {Math.round((data.national_vote_share[name] ?? 0) * 100)}% {t('districts.nationalVotes')}
                </div>
              ))}
            </div>
          </div>

          {/* Dual hémicycles */}
          <Row className="g-3 mb-3">
            <Col xs={12} sm={6}>
              <div className="border rounded p-2">
                <Hémicycle
                  seats={data.parliament_fptp}
                  candidateNames={candidateNames}
                  totalSeats={data.num_districts}
                  label={`FPTP — ${t('districts.fptp')}`}
                />
              </div>
            </Col>
            <Col xs={12} sm={6}>
              <div className="border rounded p-2">
                <Hémicycle
                  seats={data.parliament_proportional}
                  candidateNames={candidateNames}
                  totalSeats={data.num_districts}
                  label={`PR — ${t('districts.proportional')}`}
                />
              </div>
            </Col>
          </Row>

          {/* National vote share bar */}
          <div className="mb-3">
            <div className="small text-muted mb-1">{t('districts.nationalVoteShare')}</div>
            <div style={{ display: 'flex', height: 28, borderRadius: 4, overflow: 'hidden', width: '100%' }}>
              {candidateNames
                .filter((n) => (data.national_vote_share[n] ?? 0) > 0)
                .sort((a, b) => (data.national_vote_share[b] ?? 0) - (data.national_vote_share[a] ?? 0))
                .map((name) => {
                  const pct = Math.round((data.national_vote_share[name] ?? 0) * 100);
                  return (
                    <div
                      key={name}
                      style={{
                        flex: data.national_vote_share[name] ?? 0,
                        background: candidateColor(name, candidateNames),
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#fff', fontSize: '0.72rem', fontWeight: 600,
                        transition: 'flex 0.4s',
                      }}
                      title={`${name}: ${pct}%`}
                    >
                      {pct >= 8 ? `${name[0]} ${pct}%` : ''}
                    </div>
                  );
                })}
            </div>
            <div className="d-flex gap-2 mt-1 flex-wrap" style={{ fontSize: '0.72rem' }}>
              <span className="text-muted">{t('districts.nationalVotes')} ↑</span>
              {candidateNames.map((n) => (
                <span key={n}>
                  {n}: <strong>{Math.round((data.national_vote_share[n] ?? 0) * 100)}%</strong>
                  {' → '}
                  <span style={{ color: candidateColor(n, candidateNames) }}>
                    {data.parliament_fptp[n] ?? 0} {t('districts.seats')} FPTP
                  </span>
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DistrictMap;
