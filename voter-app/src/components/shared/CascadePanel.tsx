/**
 * CascadePanel — simulates sequential voting with information cascades
 * (Bikhchandani, Hirshleifer & Welch, 1992).
 *
 * Voters see previous votes and may follow the public signal instead of
 * their private (sincere) preference.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts';
import { useElection } from '../../context/ElectionContext';
import PinToCentralButton from './PinToCentralButton';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';
const DEBOUNCE_MS = 400;
const ANIM_STEP_MS = 80;

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoteEntry {
  voter_id:        number;
  sincere_choice:  string;
  actual_vote:     string;
  followed_cascade: boolean;
}

interface ComparisonRun {
  strength:     number;
  winner:       string;
  cascade_rate: number;
}

interface CascadeData {
  sincere_winner:          string;
  cascade_winner:          string;
  cascade_occurred:        boolean;
  vote_sequence:           VoteEntry[];
  cascade_start_at:        number | null;
  cascade_strength_curve:  { strength: number; winner: string; cascade_rate: number }[];
  comparison_runs:         ComparisonRun[];
  candidates:              string[];
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Running tally ─────────────────────────────────────────────────────────────

function tallyUpTo(seq: VoteEntry[], n: number): Record<string, number> {
  const tally: Record<string, number> = {};
  for (let i = 0; i < n && i < seq.length; i++) {
    const v = seq[i].actual_vote;
    tally[v] = (tally[v] ?? 0) + 1;
  }
  return tally;
}

// ── Timeline SVG ──────────────────────────────────────────────────────────────

const TIMELINE_H = 70;
const DOT_R = 4;
const DOT_MARGIN = 2;

interface TimelineProps {
  sequence:        VoteEntry[];
  visibleN:        number;
  cascadeStartAt:  number | null;
  candidates:      string[];
}

const TimelineSVG: React.FC<TimelineProps> = ({ sequence, visibleN, cascadeStartAt, candidates }) => {
  const n   = sequence.length;
  if (n === 0) return null;

  const cellW = Math.max(DOT_R * 2 + DOT_MARGIN, 600 / n);
  const svgW  = Math.max(600, n * cellW);

  // cascade line x position
  const cascadeX = cascadeStartAt != null
    ? (cascadeStartAt / n) * svgW + cellW / 2
    : null;

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg
        data-testid="cascade-timeline-svg"
        width={svgW}
        height={TIMELINE_H}
        style={{ display: 'block' }}
      >
        {/* cascade start line */}
        {cascadeX != null && (
          <line
            data-testid="cascade-start-line"
            x1={cascadeX} y1={0} x2={cascadeX} y2={TIMELINE_H}
            stroke="#dc3545" strokeWidth={1.5} strokeDasharray="4 2"
          />
        )}

        {sequence.slice(0, visibleN).map((entry, i) => {
          const cx = i * cellW + cellW / 2;
          const cy = TIMELINE_H / 2;
          const color = candColor(entry.actual_vote, candidates);
          return (
            <g key={i}>
              {/* dashed ring for cascade-followers */}
              {entry.followed_cascade && (
                <circle
                  data-testid="cascade-follower-ring"
                  cx={cx} cy={cy} r={DOT_R + 3}
                  fill="none" stroke={color} strokeWidth={1} strokeDasharray="2 2"
                />
              )}
              <circle cx={cx} cy={cy} r={DOT_R} fill={color} opacity={0.85} />
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// ── Running tally bar ─────────────────────────────────────────────────────────

interface TallyBarProps {
  tally:      Record<string, number>;
  total:      number;
  candidates: string[];
}

const TallyBar: React.FC<TallyBarProps> = ({ tally, total, candidates }) => (
  <div className="d-flex gap-2 flex-wrap mt-2" data-testid="tally-bar">
    {candidates.map((c) => {
      const n    = tally[c] ?? 0;
      const pct  = total > 0 ? Math.round((n / total) * 100) : 0;
      const color = candColor(c, candidates);
      return (
        <div key={c} className="d-flex align-items-center gap-1" style={{ fontSize: '0.8rem' }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
          <span style={{ color }}>{c}</span>
          <strong>{pct}%</strong>
          <span className="text-muted">({n})</span>
        </div>
      );
    })}
  </div>
);

// ── Comparison badges ─────────────────────────────────────────────────────────

interface ComparisonProps {
  runs:       ComparisonRun[];
  candidates: string[];
  t:          (k: string) => string;
}

const ComparisonBadges: React.FC<ComparisonProps> = ({ runs, candidates, t }) => (
  <div className="d-flex gap-3 flex-wrap mt-3" data-testid="comparison-badges">
    {runs.map((r) => {
      const color = candColor(r.winner, candidates);
      return (
        <div key={r.strength} className="text-center" style={{ minWidth: 90 }}>
          <div className="text-muted" style={{ fontSize: '0.7rem' }}>
            {t('cascade.strength')} {r.strength.toFixed(1)}
          </div>
          <Badge
            style={{ background: color, fontSize: '0.75rem' }}
            data-testid={`comparison-badge-${r.strength.toFixed(1)}`}
          >
            {r.winner}
          </Badge>
          <div className="text-muted" style={{ fontSize: '0.7rem' }}>
            {Math.round(r.cascade_rate * 100)}% {t('cascade.followed')}
          </div>
        </div>
      );
    })}
  </div>
);

// ── Main panel ────────────────────────────────────────────────────────────────

const CascadePanel: React.FC = () => {
  const { t }    = useTranslation();
  const { config } = useElection();

  const [cascadeStrength,   setCascadeStrength]   = useState(0.5);
  const [observationWindow, setObservationWindow] = useState(10);
  const [data,              setData]              = useState<CascadeData | null>(null);
  const [loading,           setLoading]           = useState(false);
  const [error,             setError]             = useState<string | null>(null);
  const [animIndex,         setAnimIndex]         = useState(0);
  const [playing,           setPlaying]           = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const animRef     = useRef<ReturnType<typeof setInterval> | null>(null);

  const runSimulation = useCallback(async (strength: number, window: number) => {
    setLoading(true);
    setError(null);
    setPlaying(false);
    setAnimIndex(0);
    try {
      const res = await axios.post(`${API}/api/election/cascade`, {
        candidates:         config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
        num_voters:         config.num_voters,
        ideology:           config.ideology,
        seed:               config.seed,
        cascade_strength:   strength,
        observation_window: window,
      });
      setData(res.data);
    } catch {
      setError(t('cascade.error'));
    } finally {
      setLoading(false);
    }
  }, [config, t]);

  const handleSimulate = () => runSimulation(cascadeStrength, observationWindow);

  // Debounced slider recalculation
  const handleStrengthChange = (v: number) => {
    setCascadeStrength(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(v, observationWindow), DEBOUNCE_MS);
  };

  // Animation
  useEffect(() => {
    if (animRef.current) clearInterval(animRef.current);
    if (!playing || !data) return;
    const total = data.vote_sequence.length;
    animRef.current = setInterval(() => {
      setAnimIndex((prev) => {
        if (prev >= total) {
          setPlaying(false);
          clearInterval(animRef.current!);
          return prev;
        }
        return prev + 1;
      });
    }, ANIM_STEP_MS);
    return () => { if (animRef.current) clearInterval(animRef.current); };
  }, [playing, data]);

  const handlePlayPause = () => {
    if (!data) return;
    if (animIndex >= data.vote_sequence.length) setAnimIndex(0);
    setPlaying((p) => !p);
  };

  const visibleN   = data ? (playing || animIndex > 0 ? animIndex : data.vote_sequence.length) : 0;
  const tally      = data ? tallyUpTo(data.vote_sequence, visibleN) : {};
  const visibleTotal = Object.values(tally).reduce((a, b) => a + b, 0);
  const candidates = data?.candidates ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={5}>
          <Form.Label className="small mb-0">
            {t('cascade.strengthSlider')}: <strong>{cascadeStrength.toFixed(2)}</strong>
          </Form.Label>
          <Form.Range
            data-testid="cascade-strength-slider"
            min={0} max={1} step={0.05}
            value={cascadeStrength}
            onChange={(e) => handleStrengthChange(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={3}>
          <Form.Label className="small mb-0">{t('cascade.window')}</Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={0} max={50}
            value={observationWindow}
            onChange={(e) => setObservationWindow(Math.max(0, Math.min(50, Number(e.target.value))))}
          />
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            onClick={handleSimulate}
            disabled={loading}
          >
            {loading ? <Spinner size="sm" animation="border" /> : t('cascade.run')}
          </Button>
        </Col>
        {data && (
          <Col xs={12} sm="auto">
            <PinToCentralButton
              type="cascade"
              icon="📡"
              label={t('cascade.cascadeWinner')}
              summary={
                data.sincere_winner !== data.cascade_winner
                  ? `${data.sincere_winner} → ${data.cascade_winner}`
                  : `${t('cascade.sincereWinner')}: ${data.sincere_winner}`
              }
              methodsChanged={data.sincere_winner !== data.cascade_winner ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {/* Prompt */}
      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('cascade.prompt')}</Alert>
      )}

      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Winner badges */}
          <div className="d-flex gap-2 flex-wrap mb-3">
            <Badge bg="secondary">{t('cascade.sincereWinner')}: {data.sincere_winner}</Badge>
            <Badge
              data-testid="cascade-winner-badge"
              bg={data.cascade_occurred ? 'danger' : 'success'}
            >
              {t('cascade.cascadeWinner')}: {data.cascade_winner}
            </Badge>
            {data.cascade_occurred && (
              <Badge bg="warning" text="dark" data-testid="cascade-occurred-badge">
                {t('cascade.cascadeOccurred')}
              </Badge>
            )}
            {data.cascade_start_at != null && (
              <Badge bg="info" text="dark" data-testid="cascade-start-badge">
                {t('cascade.cascadeStartAt')} #{data.cascade_start_at + 1}
              </Badge>
            )}
          </div>

          {/* Comparison runs */}
          <ComparisonBadges runs={data.comparison_runs} candidates={candidates} t={t} />

          {/* Timeline */}
          <div className="mt-4">
            <div className="d-flex align-items-center gap-2 mb-2">
              <span className="fw-semibold" style={{ fontSize: '0.85rem' }}>
                {t('cascade.timelineTitle')}
              </span>
              <Button
                size="sm"
                variant="outline-secondary"
                onClick={handlePlayPause}
                data-testid="play-button"
              >
                {playing ? '⏸' : '▶'}
              </Button>
              {(playing || animIndex > 0) && (
                <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {visibleN} / {data.vote_sequence.length}
                </span>
              )}
            </div>
            <TallyBar tally={tally} total={visibleTotal} candidates={candidates} />
            <TimelineSVG
              sequence={data.vote_sequence}
              visibleN={visibleN}
              cascadeStartAt={data.cascade_start_at}
              candidates={candidates}
            />
            <div className="d-flex gap-3 mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
              <span>● {t('cascade.legendVote')}</span>
              <span>◌ {t('cascade.legendFollowed')}</span>
              <span style={{ color: '#dc3545' }}>╎ {t('cascade.legendCascadeStart')}</span>
            </div>
          </div>

          {/* Strength curve */}
          <div className="mt-4" data-testid="cascade-curve-chart">
            <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
              {t('cascade.curveTitle')}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.cascade_strength_curve} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="strength" tickFormatter={(v: number) => v.toFixed(1)} />
                <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Legend />
                <ReferenceLine x={cascadeStrength} stroke="#6c757d" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="cascade_rate"
                  name={t('cascade.cascadeRate')}
                  stroke="#dc3545"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
};

export default CascadePanel;
