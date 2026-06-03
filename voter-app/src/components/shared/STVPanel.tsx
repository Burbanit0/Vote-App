/**
 * STVPanel — Single Transferable Vote visualisation.
 *
 * Shows:
 *   A) Step-by-step STV rounds with Sankey-style transfer arrows
 *   B) Three hémicycles: STV vs D'Hondt vs FPTP
 *   C) Quota display with per-candidate progress bars
 */
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface STVRound {
  round:     number;
  action:    'elect' | 'eliminate' | 'auto_elect';
  candidate: string;
  tallies:   Record<string, number>;
  transfers: Record<string, number>;
}

interface STVData {
  stv:    { elected: string[]; quota: number; rounds: STVRound[]; seats: Record<string, number> };
  dhondt: { seats: Record<string, number>; elected: string[] };
  fptp:   { seats: Record<string, number>; elected: string[] };
  vote_shares:           Record<string, number>;
  num_seats:             number;
  quota:                 number;
  quota_type:            string;
  distortion_stv_dhondt: number;
  distortion_stv_fptp:   number;
  candidates:            string[];
}

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22', '#2A9D8F', '#E76F51'];
function candColor(name: string, names: string[]) {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── Hémicycle SVG ─────────────────────────────────────────────────────────────

interface HémicycleProps {
  seats:     Record<string, number>;
  names:     string[];
  total:     number;
  label:     string;
}

const Hémicycle: React.FC<HémicycleProps> = ({ seats, names, total, label }) => {
  const W = 220; const H = 125; const cx = W / 2; const cy = H - 8;
  const rI = 40; const rO = 100;
  const parties = names.filter(n => (seats[n] ?? 0) > 0);
  let cum = Math.PI;
  const segs = parties.map(n => {
    const span = ((seats[n] ?? 0) / total) * Math.PI;
    const s = { name: n, a1: cum, a2: cum + span };
    cum += span;
    return s;
  });
  function arc(r: number, a: number): [number, number] {
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  }
  function path(r1: number, r2: number, a1: number, a2: number) {
    const [x1,y1]=arc(r1,a1);const [x2,y2]=arc(r2,a1);
    const [x3,y3]=arc(r2,a2);const [x4,y4]=arc(r1,a2);
    const la=a2-a1>Math.PI?1:0;
    return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
  }
  return (
    <div className="text-center">
      <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: 2 }}>{label}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 240 }}>
        {segs.map(s => (
          <path key={s.name} d={path(rI, rO, s.a1, s.a2)}
            fill={candColor(s.name, names)} stroke="#fff" strokeWidth={1.5}>
            <title>{s.name}: {seats[s.name]} siège(s)</title>
          </path>
        ))}
        <line x1={arc(rI-3,Math.PI/2)[0]} y1={arc(rI-3,Math.PI/2)[1]}
              x2={arc(rO+3,Math.PI/2)[0]} y2={arc(rO+3,Math.PI/2)[1]}
              stroke="#dc3545" strokeWidth={1.5} strokeDasharray="3 2" />
      </svg>
      <div className="d-flex flex-wrap gap-1 justify-content-center mt-1">
        {parties.map(n => (
          <span key={n} style={{ fontSize: '0.68rem' }}>
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 1,
              background: candColor(n, names), marginRight: 2 }} />
            {n} ({seats[n]})
          </span>
        ))}
      </div>
    </div>
  );
};

// ── STV Round step ────────────────────────────────────────────────────────────

interface RoundStepProps {
  round:     STVRound;
  quota:     number;
  names:     string[];
  elected:   Set<string>;
  eliminated: Set<string>;
}

const RoundStep: React.FC<RoundStepProps> = ({ round, quota, names, elected, eliminated }) => {
  const { t } = useTranslation();
  const isElect = round.action === 'elect' || round.action === 'auto_elect';
  const color   = isElect ? '#007A33' : '#B71C1C';

  return (
    <div
      className="border rounded p-2 mb-2"
      style={{ borderLeft: `4px solid ${isElect ? '#007A33' : '#dc3545'}`, fontSize: '0.8rem' }}
      data-testid={`stv-round-${round.round}`}
    >
      <div className="d-flex align-items-center gap-2 mb-1">
        <Badge style={{ background: color, fontSize: '0.68rem' }}>
          {t(`stv.action_${round.action}`)}
        </Badge>
        <strong>{round.candidate}</strong>
        {isElect && <span style={{ color: '#007A33' }}>✓</span>}
        {round.action === 'eliminate' && <span style={{ color: '#B71C1C' }}>✗</span>}
      </div>

      {/* Candidate tallies as mini bars */}
      <div className="d-flex flex-column gap-1">
        {names.filter(n => !eliminated.has(n)).map(n => {
          const tally    = round.tallies[n] ?? 0;
          const transfer = round.transfers[n] ?? 0;
          const pct      = Math.min(100, Math.round((tally / quota) * 100));
          const isElected = elected.has(n);
          return (
            <div key={n} className="d-flex align-items-center gap-1">
              <span style={{ minWidth: 60, fontSize: '0.7rem', color: candColor(n, names),
                opacity: isElected ? 0.5 : 1 }}>
                {n}
              </span>
              <div style={{ flex: 1, height: 8, background: '#e9ecef', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{
                  width: `${pct}%`, height: '100%',
                  background: candColor(n, names), opacity: isElected ? 0.4 : 0.85,
                  borderRadius: 4, transition: 'width 0.3s',
                }} />
              </div>
              <span style={{ minWidth: 34, fontSize: '0.68rem', textAlign: 'right' }}>
                {tally.toFixed(1)}
              </span>
              {transfer > 0.005 && (
                <span style={{ fontSize: '0.65rem', color: '#007A33' }}>+{transfer.toFixed(1)}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const STVPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [numSeats,   setNumSeats]   = useState(3);
  const [quotaType,  setQuotaType]  = useState<'droop' | 'hare'>('droop');
  const sim = $api.useMutation('post', '/api/v2/election/stv');
  const data: STVData | null = (sim.data as STVData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('stv.error') : null;
  const [stepIdx,    setStepIdx]    = useState(0);

  function run() {
    setStepIdx(0);
    sim.mutate({ body: {
      candidates: config.candidates,
      num_voters: config.num_voters,
      ideology:   config.ideology,
      seed:       config.seed,
      num_seats:  numSeats,
      quota_type: quotaType,
    } });
  }

  // Build cumulative elected/eliminated sets up to current step
  const { electedSoFar, eliminatedSoFar } = useMemo(() => {
    if (!data) return { electedSoFar: new Set<string>(), eliminatedSoFar: new Set<string>() };
    const elec = new Set<string>();
    const elim = new Set<string>();
    data.stv.rounds.slice(0, stepIdx + 1).forEach(r => {
      if (r.action === 'elect' || r.action === 'auto_elect') elec.add(r.candidate);
      if (r.action === 'eliminate') elim.add(r.candidate);
    });
    return { electedSoFar: elec, eliminatedSoFar: elim };
  }, [data, stepIdx]);

  const names     = data?.candidates ?? [];
  const numRounds = data?.stv.rounds.length ?? 0;

  // Initial tallies (first round round 0 tally or vote_shares * num_voters)
  const initialTallies: Record<string, number> = useMemo(() => {
    if (!data) return {};
    const n = config.num_voters;
    return Object.fromEntries(names.map(c => [c, (data.vote_shares[c] ?? 0) * n]));
  }, [data, names, config.num_voters]);

  const currentRound = data?.stv.rounds[stepIdx];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('stv.numSeats')}: <strong>{numSeats}</strong>
          </label>
          <Range min={2} max={Math.max(2, config.candidates.length - 1)} step={1}
            value={numSeats} onChange={e => setNumSeats(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={3}>
          <label className="mb-1 inline-block small mb-0">{t('stv.quotaType')}</label>
          <Select size="sm" value={quotaType}
            onChange={e => setQuotaType(e.target.value as 'droop' | 'hare')}>
            <option value="droop">Droop (Q = ⌊N/(s+1)⌋ + 1)</option>
            <option value="hare">Hare (Q = N/s)</option>
          </Select>
        </Col>
        <Col xs={12} sm={3} className="d-flex align-items-end">
          <Button variant="primary" className="w-100" onClick={run} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `🔄 ${t('stv.run')}`}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('stv.prompt')}</Alert>}

      {data && (
        <>
          {/* Quota display */}
          <Alert variant="secondary" className="py-2 mb-3" style={{ fontSize: '0.82rem' }}>
            <strong>{t('stv.quotaLabel')}</strong>:{' '}
            Q = ⌊{config.num_voters} / ({numSeats}+1)⌋ + 1 = <strong>{data.quota}</strong>
            {' '}{t('stv.votes')} &nbsp;·&nbsp;
            {data.quota_type === 'droop' ? 'Quota de Droop' : 'Quota de Hare'}
          </Alert>

          <Row className="g-3">
            {/* Left: STV stepper */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('stv.stepperTitle')}
                <Badge variant="secondary" className="ms-2" style={{ fontSize: '0.68rem' }}>
                  {stepIdx + 1} / {numRounds}
                </Badge>
              </div>

              {/* Nav */}
              <div className="d-flex gap-2 align-items-center mb-2">
                <Button size="sm" variant="outline-secondary"
                  disabled={stepIdx <= 0} onClick={() => setStepIdx(s => s - 1)}>‹</Button>
                <Range min={0} max={Math.max(0, numRounds - 1)} step={1} value={stepIdx}
                  onChange={e => setStepIdx(Number(e.target.value))}
                  style={{ flex: 1 }} data-testid="step-slider" />
                <Button size="sm" variant="outline-secondary"
                  disabled={stepIdx >= numRounds - 1} onClick={() => setStepIdx(s => s + 1)}>›</Button>
              </div>

              {/* Elected so far */}
              <div className="d-flex flex-wrap gap-1 mb-2">
                {data.stv.elected.map((c, i) => (
                  <Badge
                    key={c}
                    style={{
                      background: electedSoFar.has(c) ? candColor(c, names) : '#dee2e6',
                      color: electedSoFar.has(c) ? '#fff' : '#6c757d',
                      fontSize: '0.72rem',
                    }}
                    data-testid={electedSoFar.has(c) ? `elected-badge-${c}` : `pending-badge-${c}`}
                  >
                    {electedSoFar.has(c) ? '✓ ' : ''}{c}
                  </Badge>
                ))}
              </div>

              {/* Quota progress bars */}
              <div className="mb-2">
                {names.map(n => {
                  const tally = currentRound?.tallies[n]
                    ?? (stepIdx === 0 ? initialTallies[n] : 0);
                  const pct = Math.min(100, Math.round((tally / data.quota) * 100));
                  return (
                    <div key={n} className="d-flex align-items-center gap-1 mb-1"
                      style={{ opacity: eliminatedSoFar.has(n) ? 0.3 : 1 }}>
                      <span style={{ minWidth: 65, fontSize: '0.72rem', color: candColor(n, names) }}>{n}</span>
                      <Progress now={pct} max={100} style={{ flex: 1, height: 8 }}
                        variant={electedSoFar.has(n) ? 'success' : undefined}
                        label={electedSoFar.has(n) ? '✓' : undefined}
                      />
                      <span style={{ minWidth: 36, fontSize: '0.7rem', textAlign: 'right' }}>
                        {tally?.toFixed(1) ?? '—'}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Current round detail */}
              {currentRound && (
                <RoundStep
                  round={currentRound}
                  quota={data.quota}
                  names={names}
                  elected={electedSoFar}
                  eliminated={eliminatedSoFar}
                />
              )}
            </Col>

            {/* Right: 3 hémicycles comparison */}
            <Col xs={12} lg={6}>
              <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
                {t('stv.comparisonTitle')}
              </div>

              <Row className="g-2 mb-3">
                <Col xs={4}>
                  <Hémicycle seats={data.stv.seats} names={names}
                    total={numSeats} label={`STV`} />
                </Col>
                <Col xs={4}>
                  <Hémicycle seats={data.dhondt.seats} names={names}
                    total={numSeats} label={`D'Hondt`} />
                </Col>
                <Col xs={4}>
                  <Hémicycle seats={data.fptp.seats} names={names}
                    total={numSeats} label={`FPTP`} />
                </Col>
              </Row>

              {/* Distortion badges */}
              <div className="d-flex flex-wrap gap-2 mb-3">
                <Badge
                  variant={data.distortion_stv_dhondt > 0 ? 'warning' : 'success'}
                  style={{ fontSize: '0.72rem' }}
                  data-testid="distortion-stv-dhondt"
                >
                  STV vs D'Hondt: ±{data.distortion_stv_dhondt} {t('stv.seats')}
                </Badge>
                <Badge
                  variant={data.distortion_stv_fptp > 0 ? 'danger' : 'success'}
                  style={{ fontSize: '0.72rem' }}
                  data-testid="distortion-stv-fptp"
                >
                  STV vs FPTP: ±{data.distortion_stv_fptp} {t('stv.seats')}
                </Badge>
              </div>

              {/* National vote share vs STV seats */}
              <div style={{ fontSize: '0.78rem' }}>
                <div className="fw-semibold mb-1">{t('stv.voteShareVsSeats')}</div>
                {names.map(n => {
                  const votePct  = Math.round((data.vote_shares[n] ?? 0) * 100);
                  const seatsPct = Math.round(((data.stv.seats[n] ?? 0) / numSeats) * 100);
                  const diff     = seatsPct - votePct;
                  return (
                    <div key={n} className="d-flex gap-2 align-items-center mb-1">
                      <span style={{ minWidth: 65, color: candColor(n, names) }}>{n}</span>
                      <span>{votePct}% {t('stv.votes')}</span>
                      <span>→</span>
                      <span>{data.stv.seats[n] ?? 0} {t('stv.seats')}</span>
                      <span style={{ color: diff > 0 ? '#007A33' : diff < 0 ? '#dc3545' : '#6c757d', fontSize: '0.7rem' }}>
                        {diff >= 0 ? `+${diff}` : `${diff}`}pp
                      </span>
                    </div>
                  );
                })}
              </div>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default STVPanel;
