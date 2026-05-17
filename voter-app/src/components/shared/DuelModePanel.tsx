/**
 * DuelModePanel — side-by-side method comparison on the same ElectionResult.
 *
 * Two method panels (left / right) sharing the same electorate.
 * A central comparison band shows convergence (green) or divergence (red).
 * Changing a method triggers a CSS flip animation on the winner badge.
 * Pedagogical text is derived from Condorcet winner, Bayesian Regret, and blank rate.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row } from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from 'recharts';
import { ElectionResult } from '../../services/electionApi';
import { useNavigate } from 'react-router';

// ── Constants ─────────────────────────────────────────────────────────────────

const METHODS = [
  'plurality', 'two_round', 'borda', 'approval', 'irv', 'coombs', 'bucklin',
  'minimax', 'schulze', 'kemeny_young', 'positional_score',
  'simple_score', 'star_voting', 'median_voting', 'mean_median_hybrid',
  'variance_based',
];

const COLOR_LEFT  = '#005CAB';
const COLOR_RIGHT = '#C8590A';

const CANDIDATE_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22',
];

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Approximate vote shares via Voronoi (nearest candidate per voter). */
function approximateShares(
  voters:     { x: number; y: number }[],
  candidates: { name: string; x: number; y: number }[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  candidates.forEach((c) => { counts[c.name] = 0; });
  for (const v of voters) {
    let best = candidates[0];
    let bestD = Infinity;
    for (const c of candidates) {
      const d = (v.x - c.x) ** 2 + (v.y - c.y) ** 2;
      if (d < bestD) { bestD = d; best = c; }
    }
    counts[best.name]++;
  }
  const total = voters.length || 1;
  const result: Record<string, number> = {};
  candidates.forEach((c) => { result[c.name] = Math.round((counts[c.name] / total) * 100); });
  return result;
}

/** Auto-generate a pedagogical note based on available metrics. */
function buildNote(
  result:  ElectionResult,
  mA:      string,
  mB:      string,
  winnerA: string | null,
  winnerB: string | null,
  t:       (k: string, opts?: Record<string, unknown>) => string,
): string {
  if (!winnerA || !winnerB) return '';
  const { condorcet_winner, blank_rate } = result;
  const regretA = result.methods[mA]?.bayesian_regret;
  const regretB = result.methods[mB]?.bayesian_regret;

  if (winnerA === winnerB) {
    return t('duel.pedagogicalAgree', { method: mA, winner: winnerA });
  }

  // Condorcet spoiler?
  if (condorcet_winner && winnerA !== condorcet_winner && winnerB === condorcet_winner) {
    return t('duel.pedagogicalCondorcet', { miss: mA, hit: mB, cw: condorcet_winner, winner: winnerA });
  }
  if (condorcet_winner && winnerB !== condorcet_winner && winnerA === condorcet_winner) {
    return t('duel.pedagogicalCondorcet', { miss: mB, hit: mA, cw: condorcet_winner, winner: winnerB });
  }

  // Regret comparison?
  if (regretA != null && regretB != null && Math.abs(regretA - regretB) > 0.005) {
    const better = regretA < regretB ? mA : mB;
    const regret = Math.min(regretA, regretB).toFixed(4);
    return t('duel.pedagogicalRegret', { winA: winnerA, winB: winnerB, better, regret, mA, mB });
  }

  // Blank rate?
  if (blank_rate > 0.15) {
    return t('duel.pedagogicalBlank', { winA: winnerA, winB: winnerB, pct: Math.round(blank_rate * 100), mA, mB });
  }

  return t('duel.pedagogicalDefault', { winA: winnerA, winB: winnerB, mA, mB });
}

// ── Flip-animated winner badge ────────────────────────────────────────────────

const FlipBadge: React.FC<{ winner: string | null; color: string }> = ({ winner, color }) => {
  const [visible, setVisible] = useState(true);
  const [display, setDisplay] = useState(winner);
  const prevRef = useRef(winner);

  useEffect(() => {
    if (winner === prevRef.current) return;
    prevRef.current = winner;
    // Phase 1: flip out
    setVisible(false);
    const t1 = setTimeout(() => {
      setDisplay(winner);
      // Phase 2: flip in
      setVisible(true);
    }, 160);
    return () => clearTimeout(t1);
  }, [winner]);

  return (
    <div
      data-testid="winner-badge-wrapper"
      style={{
        transform:  visible ? 'rotateY(0deg)' : 'rotateY(90deg)',
        transition: 'transform 0.15s ease',
        display:    'inline-block',
      }}
    >
      <Badge
        style={{
          background: color,
          fontSize:   '1rem',
          padding:    '0.4em 0.75em',
        }}
      >
        {display ?? '—'}
      </Badge>
    </div>
  );
};

// ── Single method panel ───────────────────────────────────────────────────────

interface PanelProps {
  result:     ElectionResult;
  method:     string;
  color:      string;
  shareData:  { name: string; pct: number; color: string }[];
  onChange:   (m: string) => void;
  side:       'left' | 'right';
}

const MethodPanel: React.FC<PanelProps> = ({ result, method, color, shareData, onChange, side }) => {
  const { t } = useTranslation();
  const md         = result.methods[method];
  const winner     = md?.winner ?? null;
  const regret     = md?.bayesian_regret;
  const majSat     = md?.majority_satisfaction;
  const isCondorcet = winner !== null && winner === result.condorcet_winner;
  const kemenyApprox = method === 'kemeny_young' && (result.methods[method] as any)?.kemeny_exact === false;

  return (
    <div
      className="border rounded p-3 h-100"
      style={{ borderColor: color, borderWidth: 2, borderStyle: 'solid' }}
      data-testid={`panel-${side}`}
    >
      <Form.Select
        size="sm"
        value={method}
        onChange={(e) => onChange(e.target.value)}
        className="mb-3"
        style={{ borderLeft: `4px solid ${color}` }}
        data-testid={`method-select-${side}`}
      >
        {METHODS.map((m) => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
      </Form.Select>

      {/* Winner badge with flip animation */}
      <div className="text-center mb-2">
        <div className="text-muted mb-1" style={{ fontSize: '0.75rem' }}>
          {t('duel.winner')}
        </div>
        <FlipBadge winner={winner} color={color} />
        {isCondorcet && (
          <Badge bg="success" className="ms-1" style={{ fontSize: '0.7rem' }}>
            Condorcet ✓
          </Badge>
        )}
        {kemenyApprox && (
          <Badge bg="warning" text="dark" className="ms-1" style={{ fontSize: '0.65rem' }}>
            ~approx.
          </Badge>
        )}
      </div>

      {/* Mini bar chart (approximate vote shares via Voronoi) */}
      <div style={{ height: 120 }} data-testid={`bar-chart-${side}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={shareData} layout="vertical" margin={{ top: 2, right: 30, bottom: 2, left: 55 }}>
            <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 9 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 9 }} width={52} />
            <Tooltip formatter={(v: number) => `${v}%`} />
            <Bar dataKey="pct" radius={[0, 3, 3, 0]} isAnimationActive={false}
              style={{ transition: 'fill 0.4s ease' }}>
              {shareData.map((entry, i) => (
                <Cell key={i} fill={entry.color} opacity={entry.name === winner ? 1 : 0.4} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Metrics */}
      <div className="d-flex flex-wrap gap-2 mt-2 justify-content-center">
        {regret != null && (
          <Badge bg="secondary" style={{ fontSize: '0.7rem' }}>
            Regret: {regret.toFixed(4)}
          </Badge>
        )}
        {majSat != null && (
          <Badge bg="info" style={{ fontSize: '0.7rem' }}>
            Satisfaction: {Math.round(majSat * 100)}%
          </Badge>
        )}
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

export interface DuelModePanelProps {
  result:          ElectionResult;
  methodA:         string;
  methodB:         string;
  onMethodAChange: (m: string) => void;
  onMethodBChange: (m: string) => void;
}

const DuelModePanel: React.FC<DuelModePanelProps> = ({
  result, methodA, methodB, onMethodAChange, onMethodBChange,
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const winnerA = result.methods[methodA]?.winner ?? null;
  const winnerB = result.methods[methodB]?.winner ?? null;
  const diverge = winnerA !== null && winnerB !== null && winnerA !== winnerB;

  // Approximate vote shares (Voronoi from voters_snapshot)
  const shareData = useMemo(() => {
    const shares = approximateShares(result.voters_snapshot, result.candidates);
    return result.candidates
      .sort((a, b) => (shares[b.name] ?? 0) - (shares[a.name] ?? 0))
      .map((c, i) => ({
        name:  c.name,
        pct:   shares[c.name] ?? 0,
        color: CANDIDATE_COLORS[i % CANDIDATE_COLORS.length],
      }));
  }, [result.voters_snapshot, result.candidates]);

  const note = useMemo(
    () => buildNote(result, methodA, methodB, winnerA, winnerB, t),
    [result, methodA, methodB, winnerA, winnerB, t],
  );

  return (
    <div>
      {/* Central comparison band */}
      <div
        className="rounded py-2 px-3 mb-3 text-center"
        style={{
          background:  diverge ? '#fff3f3' : '#f0fff4',
          border:      `1px solid ${diverge ? '#dc3545' : '#007A33'}`,
          transition:  'background 0.5s ease, border-color 0.5s ease',
        }}
        data-testid="comparison-band"
      >
        {diverge ? (
          <>
            <span style={{ color: '#dc3545', fontWeight: 600 }}>
              ⚠ {t('duel.diverge')}
            </span>
            <span className="ms-2" style={{ fontSize: '0.85rem' }}>
              ← {winnerA} <span className="text-muted">vs</span> {winnerB} →
            </span>
          </>
        ) : (
          <span style={{ color: '#007A33', fontWeight: 600 }}>
            ✓ {t('duel.converge')}
            {winnerA && <span className="ms-2 text-muted fw-normal" style={{ fontSize: '0.85rem' }}>({winnerA})</span>}
          </span>
        )}
      </div>

      {/* Side-by-side panels */}
      <Row className="g-3 mb-3">
        <Col xs={12} sm={6}>
          <MethodPanel
            result={result}
            method={methodA}
            color={COLOR_LEFT}
            shareData={shareData}
            onChange={onMethodAChange}
            side="left"
          />
        </Col>
        <Col xs={12} sm={6}>
          <MethodPanel
            result={result}
            method={methodB}
            color={COLOR_RIGHT}
            shareData={shareData}
            onChange={onMethodBChange}
            side="right"
          />
        </Col>
      </Row>

      {/* Pedagogical note */}
      {note && (
        <Alert
          variant={diverge ? 'warning' : 'success'}
          className="py-2 mb-2"
          style={{ fontSize: '0.83rem' }}
          data-testid="duel-pedagogical"
        >
          {note}
        </Alert>
      )}

      {/* "Same electorate" reminder */}
      <div className="text-center text-muted" style={{ fontSize: '0.75rem' }}>
        {t('duel.sameElectorate')} ·{' '}
        <Button
          variant="link"
          size="sm"
          className="p-0"
          style={{ fontSize: '0.75rem' }}
          onClick={() => navigate('/election-lab')}
          data-testid="open-full-btn"
        >
          {t('duel.openFull')} →
        </Button>
      </div>
    </div>
  );
};

export default DuelModePanel;
