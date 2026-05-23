/**
 * AbstentionPanel — differential abstention model visualisation.
 *
 * Shows how voters demobilise round by round as their preferred candidate
 * trails in the polls, and how this can flip the election result.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useApiAction } from '../../hooks/useApi';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useElection } from '../../context/ElectionContext';
import PinToCentralButton from './PinToCentralButton';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';
const DEBOUNCE_MS = 400;

// Inline fetcher — typed (args, return) so useApiAction's generics flow.
// Kept local rather than in services/ to keep this migration minimal; the
// systematic move to services/ is tracked as follow-up to B2.
interface AbstentionArgs {
  candidates:            unknown[];
  num_voters:            number;
  ideology:              string;
  seed:                  number;
  demobilization_factor: number;
  poll_influence:        number;
  num_rounds:            number;
}
async function fetchAbstention(args: AbstentionArgs): Promise<AbstentionData> {
  const res = await axios.post<AbstentionData>(`${API}/api/election/abstention`, args);
  return res.data;
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoterSnap {
  id:               number;
  x:                number;
  y:                number;
  preferred:        string;
  abstained:        boolean;
  prob_abstention:  number;
}

interface RoundResult {
  round:            number;
  turnout:          number;
  vote_shares:      Record<string, number>;
  winner_fptp:      string;
  winner_condorcet: string | null;
  abstention_map:   VoterSnap[];
}

interface AbstentionData {
  rounds:                    RoundResult[];
  sincere_winner:            string;
  final_winner:              string;
  winner_changed:            boolean;
  turnout_by_camp:           Record<string, number>;
  candidates:                { name: string }[];
  sincere_winners_by_method?: Record<string, string | null>;
  winners_by_method?:         Record<string, string | null>;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]) {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── SVG ideology map with abstention overlay ──────────────────────────────────

const SVG_W  = 380;
const SVG_H  = 300;
const PAD    = 20;

function dx(v: number) { return PAD + ((v + 1) / 2) * (SVG_W - 2 * PAD); }
function dy(v: number) { return PAD + ((1 - v) / 2) * (SVG_H - 2 * PAD); }

interface IdeologyOverlayProps {
  snapshot:       VoterSnap[];
  candidateNames: string[];
  round:          number;
}

const IdeologyOverlay: React.FC<IdeologyOverlayProps> = ({ snapshot, candidateNames, round }) => {
  const { t } = useTranslation();
  const [hovered, setHovered] = useState<VoterSnap | null>(null);
  const [tipPos,  setTipPos]  = useState({ x: 0, y: 0 });

  const abstained = snapshot.filter(v => v.abstained).length;
  const total     = snapshot.length;

  return (
    <div style={{ position: 'relative' }}>
      <svg
        data-testid="abstention-map-svg"
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        width="100%"
        style={{ maxHeight: 280, display: 'block', userSelect: 'none' }}
      >
        {/* Grid */}
        <line x1={SVG_W / 2} y1={PAD} x2={SVG_W / 2} y2={SVG_H - PAD} stroke="#dee2e6" strokeWidth={1} />
        <line x1={PAD} y1={SVG_H / 2} x2={SVG_W - PAD} y2={SVG_H / 2} stroke="#dee2e6" strokeWidth={1} />
        <rect x={PAD} y={PAD} width={SVG_W - 2 * PAD} height={SVG_H - 2 * PAD}
          fill="none" stroke="#ced4da" strokeWidth={0.8} />

        {/* Voter dots */}
        {snapshot.map((v) => {
          const cx    = dx(v.x);
          const cy    = dy(v.y);
          const color = candColor(v.preferred, candidateNames);
          return (
            <circle
              key={v.id}
              cx={cx} cy={cy}
              r={3.5}
              fill={v.abstained ? '#adb5bd' : color}
              fillOpacity={v.abstained ? 0.25 : 0.6}
              stroke={v.abstained ? '#6c757d' : 'none'}
              strokeWidth={v.abstained ? 0.5 : 0}
              style={{ cursor: 'default', transition: 'fill 0.4s, fill-opacity 0.4s' }}
              data-testid={v.abstained ? 'abstained-voter' : 'active-voter'}
              onMouseEnter={(e) => {
                setHovered(v);
                setTipPos({ x: e.clientX, y: e.clientY });
              }}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}

        {/* Abstention count label */}
        <text x={PAD + 2} y={PAD + 12} fontSize={9} fill="#6c757d">
          {t('abstention.round')} {round} — {Math.round((1 - abstained / Math.max(total, 1)) * 100)}% {t('abstention.turnout')}
        </text>
      </svg>

      {/* Tooltip */}
      {hovered && (
        <div style={{
          position:  'fixed',
          left:      tipPos.x + 12,
          top:       tipPos.y - 10,
          background:'rgba(0,0,0,0.82)',
          color:     '#fff',
          padding:   '4px 8px',
          borderRadius: 5,
          fontSize:  '0.72rem',
          zIndex:    9000,
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
        }}>
          #{hovered.id} · {hovered.preferred}
          {' · '}P(abstention) = {Math.round(hovered.prob_abstention * 100)}%
          {' · '}
          {hovered.abstained
            ? <span style={{ color: '#dc3545' }}>{t('abstention.abstained')}</span>
            : <span style={{ color: '#28a745' }}>{t('abstention.voted')}</span>}
        </div>
      )}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const AbstentionPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [demob,     setDemob]     = useState(0.5);
  const [influence, setInfluence] = useState(0.8);
  const [numRounds, setNumRounds] = useState(3);

  const [round,   setRound]   = useState(0);
  const [playing, setPlaying] = useState(false);

  // Generic loading/error/data state lives in useApiAction. We override
  // toErrorMessage to keep the existing i18n key ("any failure" -> friendly text).
  const {
    data, loading, error, run: runFetch,
  } = useApiAction<AbstentionData, AbstentionArgs>(
    fetchAbstention,
    { toErrorMessage: () => t('abstention.error') },
  );

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timerRef    = useRef<ReturnType<typeof setTimeout> | null>(null);

  const candidateNames = config.candidates.map(c => c.name);

  const run = useCallback(async (d: number, inf: number, nr: number) => {
    setRound(0);
    setPlaying(false);
    await runFetch({
      candidates:            config.candidates,
      num_voters:            config.num_voters,
      ideology:              config.ideology,
      seed:                  config.seed,
      demobilization_factor: d,
      poll_influence:        inf,
      num_rounds:            nr,
    });
  }, [config, runFetch]);

  // Debounced re-run on slider change
  const handleChange = (d: number, inf: number, nr: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(d, inf, nr), DEBOUNCE_MS);
  };

  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  // Auto-play
  useEffect(() => {
    if (!playing || !data) return;
    if (round >= data.rounds.length - 1) { setPlaying(false); return; }
    timerRef.current = setTimeout(() => setRound(r => r + 1), 500);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, round, data]);

  const snapshot = data?.rounds[round];
  const differs  = data?.winner_changed;

  // Turnout line chart data
  const chartData = data?.rounds.map(r => ({
    round:   r.round,
    turnout: Math.round(r.turnout * 100),
    ...Object.fromEntries(candidateNames.map(n => [n, Math.round((data.turnout_by_camp[n] ?? 0) * 100)])),
  })) ?? [];

  // Camp-level turnout shows who demobilises — only after data loads
  const showCampTurnout = data && Object.keys(data.turnout_by_camp).length > 0;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('abstention.demobFactor')}: <strong>{demob.toFixed(2)}</strong>
          </Form.Label>
          <Form.Range
            min={0} max={1} step={0.05} value={demob}
            onChange={e => { const v = Number(e.target.value); setDemob(v); handleChange(v, influence, numRounds); }}
            data-testid="demob-slider"
          />
        </Col>
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('abstention.pollInfluence')}: <strong>{influence.toFixed(2)}</strong>
          </Form.Label>
          <Form.Range
            min={0} max={1} step={0.05} value={influence}
            onChange={e => { const v = Number(e.target.value); setInfluence(v); handleChange(demob, v, numRounds); }}
            data-testid="influence-slider"
          />
        </Col>
        <Col xs={12} sm={2}>
          <Form.Label className="small mb-0">
            {t('abstention.numRounds')}: <strong>{numRounds}</strong>
          </Form.Label>
          <Form.Range
            min={1} max={5} step={1} value={numRounds}
            onChange={e => { const v = Number(e.target.value); setNumRounds(v); handleChange(demob, influence, v); }}
          />
        </Col>
        <Col xs={12} sm={2}>
          <Button variant="primary" className="w-100" onClick={() => run(demob, influence, numRounds)} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `📉 ${t('abstention.run')}`}
          </Button>
        </Col>
        {data && (() => {
          // Count how many methods changed winner under abstention
          let changedCount = data.winner_changed ? 1 : 0;
          if (data.winners_by_method && data.sincere_winners_by_method) {
            changedCount = 0;
            Object.entries(data.winners_by_method).forEach(([m, w]) => {
              if (w !== data.sincere_winners_by_method![m]) changedCount += 1;
            });
          }
          return (
            <Col xs={12} sm="auto">
              <PinToCentralButton
                type="abstention"
                icon="📉"
                label={`${t('abstention.run')} — ${Math.round(demob * 100)}% démob.`}
                summary={
                  changedCount > 0
                    ? `${changedCount}/${Object.keys(data.winners_by_method ?? {}).length || 1} ${t('lab.methodsChanged')}`
                    : `${t('abstention.sincere')}: ${data.sincere_winner}`
                }
                methodsChanged={changedCount}
                winnersByMethod={data.winners_by_method}
              />
            </Col>
          );
        })()}
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('abstention.prompt')}</Alert>}

      {data && (
        <>
          {/* Winner comparison band */}
          <div
            className="rounded py-2 px-3 mb-3 text-center"
            style={{
              background:  differs ? '#fff3f3' : '#f0fff4',
              border:      `1px solid ${differs ? '#dc3545' : '#007A33'}`,
              transition:  'all 0.4s',
            }}
            data-testid="winner-comparison-band"
          >
            {differs ? (
              <span style={{ color: '#dc3545', fontWeight: 600 }}>
                ⚠ {t('abstention.winnerChanged')}
                {' — '}
                <span className="text-muted fw-normal" style={{ fontSize: '0.85rem' }}>
                  {t('abstention.sincere')}: <strong>{data.sincere_winner}</strong>
                  {' → '}
                  {t('abstention.withAbstention')}: <strong>{data.final_winner}</strong>
                </span>
              </span>
            ) : (
              <span style={{ color: '#007A33', fontWeight: 600 }}>
                ✓ {t('abstention.winnerUnchanged')} ({data.final_winner})
              </span>
            )}
          </div>

          <Row className="g-3">
            {/* Left: ideology map */}
            <Col xs={12} lg={6}>
              <div className="border rounded p-2">
                <div className="d-flex align-items-center gap-2 mb-1">
                  <Button size="sm" variant={playing ? 'warning' : 'success'}
                    onClick={() => setPlaying(!playing)} data-testid="play-button">
                    {playing ? '⏸' : '▶'} {t('abstention.round')} {round}/{numRounds}
                  </Button>
                  <Badge bg={snapshot && snapshot.turnout < 0.7 ? 'danger' : 'secondary'}>
                    {t('abstention.turnout')}: {Math.round((snapshot?.turnout ?? 0) * 100)}%
                  </Badge>
                  {snapshot?.winner_fptp && (
                    <Badge style={{ background: candColor(snapshot.winner_fptp, candidateNames) }}>
                      FPTP: {snapshot.winner_fptp}
                    </Badge>
                  )}
                </div>
                <Form.Range
                  min={0} max={data.rounds.length - 1} step={1} value={round}
                  onChange={e => { setPlaying(false); setRound(Number(e.target.value)); }}
                  data-testid="round-slider"
                />
                {snapshot && (
                  <IdeologyOverlay
                    snapshot={snapshot.abstention_map}
                    candidateNames={candidateNames}
                    round={round}
                  />
                )}
                {/* Legend */}
                <div className="d-flex flex-wrap gap-2 mt-1" style={{ fontSize: '0.72rem' }}>
                  {candidateNames.map(n => (
                    <span key={n} className="d-flex align-items-center gap-1">
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: candColor(n, candidateNames), display: 'inline-block' }} />
                      {n}
                    </span>
                  ))}
                  <span className="d-flex align-items-center gap-1">
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#adb5bd', display: 'inline-block', opacity: 0.4 }} />
                    {t('abstention.abstained')}
                  </span>
                </div>
              </div>
            </Col>

            {/* Right: turnout line chart */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('abstention.turnoutByRound')}
              </div>
              <div style={{ height: 200 }} data-testid="turnout-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
                    <XAxis dataKey="round" tick={{ fontSize: 10 }}
                      label={{ value: t('abstention.round'), position: 'insideBottom', offset: -2, fontSize: 10 }} />
                    <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(v: number) => `${v}%`} />
                    <Legend wrapperStyle={{ fontSize: '0.72rem' }} />
                    <ReferenceLine y={50} stroke="#dee2e6" strokeDasharray="3 2" />
                    {/* Overall turnout */}
                    <Line type="monotone" dataKey="turnout" name={t('abstention.globalTurnout')}
                      stroke="#212529" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                    {/* Camp turnout */}
                    {showCampTurnout && candidateNames.map(n => (
                      <Line key={n} type="monotone" dataKey={n} name={`${n} ${t('abstention.campSuffix')}`}
                        stroke={candColor(n, candidateNames)} strokeWidth={1.5}
                        strokeDasharray="4 2" dot={false} isAnimationActive={false} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Turnout by camp summary */}
              {showCampTurnout && (
                <div className="mt-2" style={{ fontSize: '0.78rem' }}>
                  <div className="fw-semibold mb-1">{t('abstention.finalTurnoutByCamp')}</div>
                  <div className="d-flex flex-wrap gap-2">
                    {candidateNames.map(n => {
                      const pct = Math.round((data.turnout_by_camp[n] ?? 0) * 100);
                      return (
                        <Badge key={n} style={{ background: candColor(n, candidateNames), fontSize: '0.72rem' }}
                          data-testid={`camp-turnout-${n}`}>
                          {n}: {pct}%
                        </Badge>
                      );
                    })}
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

export default AbstentionPanel;
