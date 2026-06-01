import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { $api } from '../../api/hooks';
import type { AdaptiveResponse } from '../../api';

// ── Types ─────────────────────────────────────────────────────────────────────
// Source of truth is the generated `AdaptiveResponse` (Phase 6 response_model).

type AdaptiveData = AdaptiveResponse;
type RoundResult  = AdaptiveResponse['rounds'][number];
type VoterSnap    = RoundResult['voter_snapshot'][number];

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];

function candidateColor(name: string, names: string[]): string {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── Ideology scatter overlay ──────────────────────────────────────────────────

interface IdeologyOverlayProps {
  snapshot: VoterSnap[];
  candidateNames: string[];
}

const IdeologyOverlay: React.FC<IdeologyOverlayProps> = ({ snapshot, candidateNames }) => {
  const W = 320;
  const H = 260;
  const PAD = 20;

  function toSvg(v: number, size: number): number {
    return PAD + ((v + 1) / 2) * (size - 2 * PAD);
  }

  return (
    <svg
      data-testid="ideology-overlay"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ maxWidth: 340, display: 'block', margin: '0 auto' }}
    >
      {/* Grid */}
      <line x1={W / 2} y1={PAD} x2={W / 2} y2={H - PAD} stroke="#dee2e6" strokeWidth={1} />
      <line x1={PAD} y1={H / 2} x2={W - PAD} y2={H / 2} stroke="#dee2e6" strokeWidth={1} />
      <text x={PAD}     y={H - 6} fontSize={8} fill="#adb5bd" textAnchor="start">Left</text>
      <text x={W - PAD} y={H - 6} fontSize={8} fill="#adb5bd" textAnchor="end">Right</text>

      {snapshot.map((v) => {
        const cx = toSvg(v.x, W);
        const cy = toSvg(-v.y, H);
        const color = candidateColor(v.effective_vote, candidateNames);
        return (
          <g key={v.id}>
            {/* Sincere vote ring (when tactical) */}
            {v.tactical && (
              <circle
                cx={cx} cy={cy} r={5}
                fill="none"
                stroke={candidateColor(v.sincere_vote, candidateNames)}
                strokeWidth={1}
                strokeDasharray="2 1"
                opacity={0.6}
              />
            )}
            {/* Effective vote dot */}
            <circle
              cx={cx} cy={cy} r={v.tactical ? 3 : 2.5}
              fill={color}
              opacity={v.tactical ? 0.9 : 0.45}
            >
              <title>
                {v.tactical
                  ? `Tactical: ${v.sincere_vote} → ${v.effective_vote}`
                  : `Sincere: ${v.sincere_vote}`}
              </title>
            </circle>
          </g>
        );
      })}
    </svg>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const AVAILABLE_METHODS = ['plurality', 'irv', 'borda', 'schulze', 'approval'];

const AdaptiveVotingPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [method, setMethod]                       = useState('plurality');
  const [numRounds, setNumRounds]                 = useState(6);
  const [strategicThreshold, setStrategicThreshold] = useState(0.15);

  const sim = $api.useMutation('post', '/api/v2/election/adaptive');
  const data: AdaptiveData | null = sim.data ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('adaptive.error') : null;
  const [revealedRound, setRevealedRound] = useState<number>(0);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const candidateNames = config.candidates.map((c) => c.name);

  const startAnimation = useCallback((total: number) => {
    setRevealedRound(0);
    let r = 0;
    function tick() {
      r++;
      setRevealedRound(r);
      if (r < total) {
        timerRef.current = setTimeout(tick, 900);
      }
    }
    timerRef.current = setTimeout(tick, 600);
  }, []);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  function run() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setRevealedRound(0);
    sim.mutate({ body: {
      candidates:           config.candidates,
      num_voters:           config.num_voters,
      ideology:             config.ideology,
      seed:                 config.seed,
      num_rounds:           numRounds,
      method,
      strategic_threshold:  strategicThreshold,
    } }, {
      onSuccess: (res) => startAnimation(res.rounds.length),
    });
  }

  // Build chart data: one row per revealed round
  const visibleRounds = data?.rounds.slice(0, revealedRound + 1) ?? [];
  const chartData = visibleRounds.map((r) => {
    const row: Record<string, number | string> = { round: r.round };
    candidateNames.forEach((n) => {
      row[n]              = Math.round((r.vote_shares[n] ?? 0) * 100);
      row[`${n}_sincere`] = Math.round((r.sincere_shares[n] ?? 0) * 100);
    });
    return row;
  });

  const currentRound     = data?.rounds[revealedRound] ?? data?.rounds[0];
  const winnerChanged    = data && data.final_winner !== data.sincere_winner;
  const highDrift        = data && data.strategic_drift > 0.15;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 align-items-end mb-3">
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">{t('adaptive.method')}</Form.Label>
          <Form.Select size="sm" value={method} onChange={(e) => setMethod(e.target.value)}>
            {AVAILABLE_METHODS.map((m) => (
              <option key={m} value={m}>{t(`adaptive.method_${m}`)}</option>
            ))}
          </Form.Select>
        </Col>
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('adaptive.numRounds')}: <strong>{numRounds}</strong>
          </Form.Label>
          <Form.Range min={2} max={10} step={1} value={numRounds}
            onChange={(e) => setNumRounds(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('adaptive.threshold')}: <strong>{Math.round(strategicThreshold * 100)}%</strong>
          </Form.Label>
          <Form.Range min={0.05} max={0.4} step={0.05} value={strategicThreshold}
            onChange={(e) => setStrategicThreshold(Number(e.target.value))} />
        </Col>
        <Col xs={12} className="d-flex gap-2">
          <Button variant="primary" onClick={run} disabled={loading}>
            {loading
              ? <><Spinner size="sm" className="me-2" />{t('adaptive.simulating')}</>
              : `⚙ ${t('adaptive.run')}`}
          </Button>
          {data && (
            <Button variant="outline-secondary" size="sm"
              onClick={() => startAnimation(data.rounds.length)}>
              ▶ {t('adaptive.replay')}
            </Button>
          )}
          {data && (
            <PinToCentralButton
              type="adaptive"
              icon="⚙"
              label={t('adaptive.run')}
              summary={
                data.final_winner !== data.sincere_winner
                  ? `${data.sincere_winner} → ${data.final_winner}`
                  : `${t('adaptive.finalWinner')}: ${data.final_winner}`
              }
              methodsChanged={data.final_winner !== data.sincere_winner ? 1 : 0}
            />
          )}
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('adaptive.prompt')}</Alert>}

      {data && (
        <>
          {/* Summary badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg="primary" data-testid="final-winner-badge">
              {t('adaptive.finalWinner')}: {data.final_winner}
            </Badge>
            <Badge bg={winnerChanged ? 'warning' : 'success'} text={winnerChanged ? 'dark' : undefined}
              data-testid="sincere-winner-badge">
              {t('adaptive.sincereWinner')}: {data.sincere_winner}
            </Badge>
            {data.converged
              ? (
                <Badge bg="success" data-testid="convergence-badge">
                  ✓ {t('adaptive.convergedAt')} {t('adaptive.round')} {data.convergence_round}
                </Badge>
              )
              : (
                <Badge bg="danger" data-testid="convergence-badge">
                  ✗ {t('adaptive.noConvergence')}
                </Badge>
              )}
            {highDrift && (
              <Badge bg="warning" text="dark" data-testid="drift-badge">
                ⚠ {t('adaptive.drift')}: +{data.strategic_drift.toFixed(3)}
              </Badge>
            )}
          </div>

          {/* Pedagogical message */}
          <Alert
            variant={winnerChanged ? 'warning' : 'success'}
            className="py-2 mb-3"
            style={{ fontSize: '0.84rem' }}
          >
            {winnerChanged
              ? t('adaptive.pedagogicalChanged', {
                  method:       method,
                  final:        data.final_winner,
                  sincere:      data.sincere_winner,
                  drift:        data.strategic_drift.toFixed(3),
                  convergence:  data.converged
                    ? t('adaptive.convergedAt') + ' ' + t('adaptive.round') + ' ' + data.convergence_round
                    : t('adaptive.noConvergence'),
                })
              : t('adaptive.pedagogicalSame', {
                  method:  method,
                  winner:  data.final_winner,
                  convergence: data.converged
                    ? t('adaptive.convergedAt') + ' ' + t('adaptive.round') + ' ' + data.convergence_round
                    : t('adaptive.noConvergence'),
                })}
          </Alert>

          <Row className="g-3">
            {/* Race chart */}
            <Col xs={12} lg={7}>
              <div className="mb-1" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {t('adaptive.raceChart')}
                {currentRound && (
                  <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.7rem' }}>
                    {t('adaptive.round')} {currentRound.round}
                    {' — '}
                    {Math.round(currentRound.strategic_voters_pct * 100)}% {t('adaptive.tactical')}
                  </Badge>
                )}
              </div>
              <div style={{ height: 240 }} data-testid="race-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
                    <XAxis
                      dataKey="round"
                      tick={{ fontSize: 10 }}
                      label={{ value: t('adaptive.round'), position: 'insideBottom', offset: -2, fontSize: 10 }}
                    />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
                    <Tooltip formatter={(v: number, name: string) => [`${v}%`, name.replace('_sincere', ' (sincere)')]} />
                    <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
                    <ReferenceLine
                      y={Math.round(strategicThreshold * 100)}
                      stroke="#dc3545" strokeDasharray="4 2"
                      label={{ value: `${Math.round(strategicThreshold * 100)}%`, fontSize: 9, fill: '#dc3545' }}
                    />
                    {candidateNames.map((name) => (
                      <React.Fragment key={name}>
                        {/* Actual (adaptive) line */}
                        <Line
                          type="monotone"
                          dataKey={name}
                          stroke={candidateColor(name, candidateNames)}
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          isAnimationActive={false}
                          name={name}
                        />
                        {/* Sincere reference (dashed) */}
                        <Line
                          type="monotone"
                          dataKey={`${name}_sincere`}
                          stroke={candidateColor(name, candidateNames)}
                          strokeWidth={1}
                          strokeDasharray="4 3"
                          dot={false}
                          isAnimationActive={false}
                          name={`${name} (sincere)`}
                          legendType="none"
                        />
                      </React.Fragment>
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#6c757d', marginTop: 2 }}>
                — {t('adaptive.adaptiveLine')} &nbsp;&nbsp;
                ╌ {t('adaptive.sincereLine')} &nbsp;&nbsp;
                <span style={{ color: '#dc3545' }}>— {t('adaptive.thresholdLine')}</span>
              </div>
            </Col>

            {/* Ideology overlay */}
            <Col xs={12} lg={5}>
              <div className="mb-1" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                {t('adaptive.ideologyOverlay')}
              </div>
              <div className="border rounded p-2">
                {currentRound && (
                  <IdeologyOverlay
                    snapshot={currentRound.voter_snapshot}
                    candidateNames={candidateNames}
                  />
                )}
                <div className="d-flex gap-3 justify-content-center mt-1"
                  style={{ fontSize: '0.7rem', color: '#6c757d' }}>
                  <span>● {t('adaptive.tacticalVoter')}</span>
                  <span>· {t('adaptive.sincereVoter')}</span>
                  <span>○ {t('adaptive.sincerePreference')}</span>
                </div>
              </div>

              {/* Per-round stats */}
              {currentRound && (
                <div className="mt-2" style={{ fontSize: '0.78rem' }}>
                  <div className="d-flex flex-wrap gap-2">
                    {candidateNames.map((n) => (
                      <span key={n}>
                        <span style={{
                          display: 'inline-block', width: 10, height: 10,
                          background: candidateColor(n, candidateNames), borderRadius: 2, marginRight: 3,
                        }} />
                        {n}: <strong>{Math.round((currentRound.vote_shares[n] ?? 0) * 100)}%</strong>
                        {n === currentRound.winner && ' ✓'}
                      </span>
                    ))}
                  </div>
                  <div className="text-muted mt-1">
                    {Math.round(currentRound.strategic_voters_pct * 100)}% {t('adaptive.tactical')}
                  </div>
                </div>
              )}
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default AdaptiveVotingPanel;
