/**
 * MultiwinnerCompare — 5-method multi-winner comparison panel.
 *
 * Shows seat allocation by STV · D'Hondt · SPAV · Phragmén · FPTP
 * on the same electorate with distortion metrics and pedagogical text.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SeatVsVotes {
  seats:    number;
  seat_pct: number;
  vote_pct: number;
  delta:    number;
}

interface MethodResult {
  seats:         Record<string, number>;
  elected:       string[];
  distortion:    number;
  seat_vs_votes: Record<string, SeatVsVotes>;
}

interface CompareData {
  methods:                 Record<string, MethodResult>;
  vote_shares:             Record<string, number>;
  proportional_reference:  Record<string, number>;
  num_seats:               number;
  candidates:              string[];
  best_method:             string;
  worst_method:            string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22', '#2A9D8F', '#E76F51'];
function candColor(name: string, names: string[]) {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

const METHOD_LABELS: Record<string, string> = {
  stv:      'STV',
  dhondt:   "D'Hondt",
  spav:     'SPAV',
  phragmen: 'Phragmén',
  fptp:     'FPTP',
};

const METHOD_ORDER = ['stv', 'dhondt', 'spav', 'phragmen', 'fptp'];

// ── Hémicycle SVG ─────────────────────────────────────────────────────────────

const Hémicycle: React.FC<{
  seats:     Record<string, number>;
  names:     string[];
  total:     number;
  label:     string;
  distortion: number;
  isBest:    boolean;
}> = ({ seats, names, total, label, distortion, isBest }) => {
  const W = 200; const H = 125; const cx = W / 2; const cy = H - 8;
  const rI = 38; const rO = 90;
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
    const [x1,y1]=arc(r1,a1); const [x2,y2]=arc(r2,a1);
    const [x3,y3]=arc(r2,a2); const [x4,y4]=arc(r1,a2);
    const la = a2-a1>Math.PI ? 1 : 0;
    return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
  }
  return (
    <div className="text-center" data-testid={`hemicycle-${label.toLowerCase().replace(/[^a-z]/g, '')}`}>
      <div style={{
        fontSize: '0.78rem', fontWeight: 600, marginBottom: 2,
        color: isBest ? '#007A33' : 'inherit',
      }}>
        {label} {isBest && '✓'}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 210 }}>
        {segs.map(s => (
          <path key={s.name} d={path(rI, rO, s.a1, s.a2)}
            fill={candColor(s.name, names)} stroke="#fff" strokeWidth={1.5}>
            <title>{s.name}: {seats[s.name]} siège(s)</title>
          </path>
        ))}
      </svg>
      <Badge
        bg={distortion > 0.1 ? 'danger' : distortion > 0.05 ? 'warning' : 'success'}
        text={distortion > 0.05 && distortion <= 0.1 ? 'dark' : undefined}
        style={{ fontSize: '0.65rem' }}
        data-testid={`distortion-badge-${label}`}
      >
        Δ {Math.round(distortion * 100)}pp
      </Badge>
    </div>
  );
};

// ── Delta cell color ──────────────────────────────────────────────────────────

function deltaColor(delta: number): React.CSSProperties {
  if (delta > 0.05)  return { background: '#d4edda', color: '#155724' };
  if (delta < -0.05) return { background: '#f8d7da', color: '#721c24' };
  return {};
}

// ── Main component ────────────────────────────────────────────────────────────

const MultiwinnerCompare: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [numSeats, setNumSeats] = useState(4);
  const sim = $api.useMutation('post', '/api/v2/election/multiwinner_compare');
  const data: CompareData | null = (sim.data as CompareData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('multiwinner.error') : null;

  function run() {
    sim.mutate({ body: {
      candidates: config.candidates,
      num_voters: config.num_voters,
      ideology:   config.ideology,
      seed:       config.seed,
      num_seats:  numSeats,
    } });
  }

  const names  = data?.candidates ?? [];
  const total  = data?.num_seats  ?? numSeats;

  // Pedagogical message
  const pedagMsg = data ? (() => {
    const bestDist  = data.methods[data.best_method]?.distortion ?? 0;
    const worstDist = data.methods[data.worst_method]?.distortion ?? 0;
    const spavBetter = (data.methods['spav']?.distortion ?? 1) < (data.methods['fptp']?.distortion ?? 0);
    if (spavBetter) {
      return t('multiwinner.pedagogicalPR', {
        best:       METHOD_LABELS[data.best_method],
        bestDist:   Math.round(bestDist * 100),
        worst:      METHOD_LABELS[data.worst_method],
        worstDist:  Math.round(worstDist * 100),
      });
    }
    return t('multiwinner.pedagogicalGeneral', {
      best: METHOD_LABELS[data.best_method],
    });
  })() : '';

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={4}>
          <Form.Label className="small mb-0">
            {t('multiwinner.numSeats')}: <strong>{numSeats}</strong>
          </Form.Label>
          <Form.Range min={2} max={Math.max(2, config.candidates.length - 1)} step={1}
            value={numSeats} onChange={e => setNumSeats(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={4} className="d-flex align-items-end">
          <Button variant="primary" className="w-100" onClick={run} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `🏛 ${t('multiwinner.run')}`}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('multiwinner.prompt')}</Alert>}

      {data && (
        <>
          {/* Pedagogical note */}
          <Alert variant="info" className="py-2 mb-3" style={{ fontSize: '0.82rem' }}
            data-testid="multiwinner-pedagogical">
            {pedagMsg}
          </Alert>

          {/* 5 hémicycles */}
          <Row className="g-2 mb-3">
            {METHOD_ORDER.map(m => (
              <Col key={m} xs={6} sm={4} md={2} style={{ minWidth: 120 }}>
                <div className="border rounded p-1">
                  <Hémicycle
                    seats={data.methods[m]?.seats ?? {}}
                    names={names}
                    total={total}
                    label={METHOD_LABELS[m]}
                    distortion={data.methods[m]?.distortion ?? 0}
                    isBest={m === data.best_method}
                  />
                </div>
              </Col>
            ))}
          </Row>

          {/* Legend */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            {names.map(n => (
              <span key={n} className="d-flex align-items-center gap-1" style={{ fontSize: '0.72rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: candColor(n, names), display: 'inline-block' }} />
                {n} ({Math.round((data.vote_shares[n] ?? 0) * 100)}% voix)
              </span>
            ))}
          </div>

          {/* Comparison table */}
          <div style={{ fontSize: '0.78rem' }}>
            <Table bordered size="sm" responsive>
              <thead className="table-light">
                <tr>
                  <th>{t('multiwinner.method')}</th>
                  {names.map(n => <th key={n} className="text-center">{n}</th>)}
                  <th className="text-center">{t('multiwinner.distortion')}</th>
                </tr>
                {/* Proportional reference row */}
                <tr style={{ background: '#f8f9fa', fontStyle: 'italic' }}>
                  <td style={{ fontSize: '0.7rem', color: '#6c757d' }}>
                    {t('multiwinner.proportional')}
                  </td>
                  {names.map(n => (
                    <td key={n} className="text-center" style={{ color: '#6c757d' }}>
                      {data.proportional_reference[n] ?? 0}
                    </td>
                  ))}
                  <td className="text-center" style={{ color: '#6c757d' }}>—</td>
                </tr>
              </thead>
              <tbody>
                {METHOD_ORDER.map(m => {
                  const md = data.methods[m];
                  return (
                    <tr key={m} style={{ fontWeight: m === data.best_method ? 600 : undefined }}>
                      <td>
                        {METHOD_LABELS[m]}
                        {m === data.best_method && (
                          <Badge bg="success" className="ms-1" style={{ fontSize: '0.6rem' }}>
                            {t('multiwinner.mostPR')}
                          </Badge>
                        )}
                      </td>
                      {names.map(n => {
                        const sv = md?.seat_vs_votes[n];
                        return (
                          <td key={n} className="text-center" style={sv ? deltaColor(sv.delta) : {}}>
                            {md?.seats[n] ?? 0}
                            {sv && Math.abs(sv.delta) > 0.02 && (
                              <span style={{ fontSize: '0.65rem', marginLeft: 2 }}>
                                ({sv.delta > 0 ? '+' : ''}{Math.round(sv.delta * 100)}pp)
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td className="text-center">
                        <Badge
                          bg={md?.distortion > 0.1 ? 'danger' : md?.distortion > 0.05 ? 'warning' : 'success'}
                          text={md?.distortion > 0.05 && md?.distortion <= 0.1 ? 'dark' : undefined}
                          style={{ fontSize: '0.65rem' }}
                        >
                          {Math.round((md?.distortion ?? 0) * 100)}pp
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </div>

          <div className="text-muted" style={{ fontSize: '0.72rem' }}>
            {t('multiwinner.tableHint')}
          </div>
        </>
      )}
    </div>
  );
};

export default MultiwinnerCompare;
