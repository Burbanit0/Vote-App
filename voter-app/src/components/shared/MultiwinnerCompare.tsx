/**
 * MultiwinnerCompare — 5-method multi-winner comparison panel.
 *
 * Shows seat allocation by STV · D'Hondt · SPAV · Phragmén · FPTP
 * on the same electorate with distortion metrics and pedagogical text.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SeatVsVotes {
  seats: number;
  seat_pct: number;
  vote_pct: number;
  delta: number;
}

interface JustifiedRepresentation {
  jr: boolean;
  pjr: boolean;
  ejr: boolean;
}

interface MethodResult {
  seats: Record<string, number>;
  elected: string[];
  distortion: number;
  seat_vs_votes: Record<string, SeatVsVotes>;
  justified_representation?: JustifiedRepresentation;
}

interface CompareData {
  methods: Record<string, MethodResult>;
  vote_shares: Record<string, number>;
  proportional_reference: Record<string, number>;
  num_seats: number;
  candidates: string[];
  best_method: string;
  worst_method: string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = [
  '#005CAB',
  '#C8590A',
  '#007A33',
  '#6c757d',
  '#9b59b6',
  '#e67e22',
  '#2A9D8F',
  '#E76F51',
];
function candColor(name: string, names: string[]) {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

const METHOD_LABELS: Record<string, string> = {
  stv: 'STV',
  dhondt: "D'Hondt",
  spav: 'SPAV',
  phragmen: 'Phragmén',
  equal_shares: 'Parts égales',
  fptp: 'FPTP',
};

const METHOD_ORDER = ['stv', 'dhondt', 'spav', 'phragmen', 'equal_shares', 'fptp'];

// Strongest proportionality axiom a committee satisfies (EJR ⊃ PJR ⊃ JR).
function strongestJR(jr?: JustifiedRepresentation): { label: string; variant: string } {
  if (!jr) return { label: '—', variant: 'secondary' };
  if (jr.ejr) return { label: 'EJR', variant: 'success' };
  if (jr.pjr) return { label: 'PJR', variant: 'success' };
  if (jr.jr) return { label: 'JR', variant: 'warning' };
  return { label: 'aucun', variant: 'danger' };
}

// ── Hémicycle SVG ─────────────────────────────────────────────────────────────

const Hémicycle: React.FC<{
  seats: Record<string, number>;
  names: string[];
  total: number;
  label: string;
  distortion: number;
  isBest: boolean;
  jr?: JustifiedRepresentation;
}> = ({ seats, names, total, label, distortion, isBest, jr }) => {
  const jrBadge = strongestJR(jr);
  const W = 200;
  const H = 125;
  const cx = W / 2;
  const cy = H - 8;
  const rI = 38;
  const rO = 90;
  const parties = names.filter((n) => (seats[n] ?? 0) > 0);
  let cum = Math.PI;
  const segs = parties.map((n) => {
    const span = ((seats[n] ?? 0) / total) * Math.PI;
    const s = { name: n, a1: cum, a2: cum + span };
    cum += span;
    return s;
  });
  function arc(r: number, a: number): [number, number] {
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  }
  function path(r1: number, r2: number, a1: number, a2: number) {
    const [x1, y1] = arc(r1, a1);
    const [x2, y2] = arc(r2, a1);
    const [x3, y3] = arc(r2, a2);
    const [x4, y4] = arc(r1, a2);
    const la = a2 - a1 > Math.PI ? 1 : 0;
    return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
  }
  return (
    <div
      className="text-center"
      data-testid={`hemicycle-${label.toLowerCase().replace(/[^a-z]/g, '')}`}
    >
      <div
        style={{
          fontSize: '0.78rem',
          fontWeight: 600,
          marginBottom: 2,
          color: isBest ? '#007A33' : 'inherit',
        }}
      >
        {label} {isBest && '✓'}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 210 }}>
        {segs.map((s) => (
          <path
            key={s.name}
            d={path(rI, rO, s.a1, s.a2)}
            fill={candColor(s.name, names)}
            stroke="#fff"
            strokeWidth={1.5}
          >
            <title>
              {s.name}: {seats[s.name]} siège(s)
            </title>
          </path>
        ))}
      </svg>
      <div className="flex flex-wrap justify-center gap-1">
        <Badge
          variant={distortion > 0.1 ? 'danger' : distortion > 0.05 ? 'warning' : 'success'}
          style={{ fontSize: '0.65rem' }}
          data-testid={`distortion-badge-${label}`}
        >
          Δ {Math.round(distortion * 100)}pp
        </Badge>
        <Badge
          variant={jrBadge.variant as React.ComponentProps<typeof Badge>['variant']}
          style={{ fontSize: '0.65rem' }}
          data-testid={`jr-badge-${label}`}
          title="Plus forte garantie de représentation justifiée satisfaite (EJR ⊃ PJR ⊃ JR)"
        >
          {jrBadge.label}
        </Badge>
      </div>
    </div>
  );
};

// ── Delta cell color ──────────────────────────────────────────────────────────

function deltaColor(delta: number): React.CSSProperties {
  if (delta > 0.05) return { background: '#d4edda', color: '#155724' };
  if (delta < -0.05) return { background: '#f8d7da', color: '#721c24' };
  return {};
}

// ── Main component ────────────────────────────────────────────────────────────

const MultiwinnerCompare: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [numSeats, setNumSeats] = useState(4);
  const sim = $api.useMutation('post', '/api/v2/election/multiwinner_compare');
  const data: CompareData | null = (sim.data as CompareData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('multiwinner.error') : null;

  // The API requires num_seats < number of candidates. The slider's max already
  // respected that, but the initial state did not — so on the default 3-candidate
  // electorate the panel opened at 4 seats and the first "Compare" always 400'd.
  // Clamp the VALUE we render and send (rather than resetting the state), so the
  // seat count comes back on its own once the field is big enough again.
  const maxSeats = Math.max(2, config.candidates.length - 1);
  const seats = Math.min(numSeats, maxSeats);

  function run() {
    sim.mutate({
      body: {
        candidates: config.candidates,
        num_voters: config.num_voters,
        ideology: config.ideology,
        seed: config.seed,
        num_seats: seats,
      },
    });
  }

  const names = data?.candidates ?? [];
  const total = data?.num_seats ?? seats;

  // Pedagogical message
  const pedagMsg = data
    ? (() => {
        const bestDist = data.methods[data.best_method]?.distortion ?? 0;
        const worstDist = data.methods[data.worst_method]?.distortion ?? 0;
        const spavBetter =
          (data.methods['spav']?.distortion ?? 1) < (data.methods['fptp']?.distortion ?? 0);
        if (spavBetter) {
          return t('multiwinner.pedagogicalPR', {
            best: METHOD_LABELS[data.best_method],
            bestDist: Math.round(bestDist * 100),
            worst: METHOD_LABELS[data.worst_method],
            worstDist: Math.round(worstDist * 100),
          });
        }
        return t('multiwinner.pedagogicalGeneral', {
          best: METHOD_LABELS[data.best_method],
        });
      })()
    : '';

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} sm={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('multiwinner.numSeats')}: <strong data-testid="mw-seats">{seats}</strong>
          </label>
          <Range
            min={2}
            max={maxSeats}
            step={1}
            value={seats}
            onChange={(e) => setNumSeats(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} sm={4} className="flex items-end">
          <Button variant="primary" className="w-full" onClick={run} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `🏛 ${t('multiwinner.run')}`}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('multiwinner.prompt')}</Alert>}

      {data && (
        <>
          {/* Pedagogical note */}
          <Alert
            variant="info"
            className="py-2 mb-3"
            style={{ fontSize: '0.82rem' }}
            data-testid="multiwinner-pedagogical"
          >
            {pedagMsg}
          </Alert>

          {/* 5 hémicycles */}
          <Row className="g-2 mb-3">
            {METHOD_ORDER.map((m) => (
              <Col key={m} xs={6} sm={4} md={2} style={{ minWidth: 120 }}>
                <div className="border border-border rounded p-1">
                  <Hémicycle
                    seats={data.methods[m]?.seats ?? {}}
                    names={names}
                    total={total}
                    label={METHOD_LABELS[m]}
                    distortion={data.methods[m]?.distortion ?? 0}
                    isBest={m === data.best_method}
                    jr={data.methods[m]?.justified_representation}
                  />
                </div>
              </Col>
            ))}
          </Row>

          {/* Justified-representation note */}
          <div
            className="text-muted-foreground mb-2"
            style={{ fontSize: '0.72rem' }}
            data-testid="jr-note"
          >
            Badge de représentation justifiée (approbation) : <strong>EJR</strong> ⊃{' '}
            <strong>PJR</strong> ⊃ <strong>JR</strong> — tout groupe cohésif de taille ≥ ℓ·n/k
            obtient une représentation proportionnelle. La méthode des <em>parts égales</em> (Rule
            X) garantit l’EJR.
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-2 mb-3">
            {names.map((n) => (
              <span key={n} className="flex items-center gap-1" style={{ fontSize: '0.72rem' }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    background: candColor(n, names),
                    display: 'inline-block',
                  }}
                />
                {n} ({Math.round((data.vote_shares[n] ?? 0) * 100)}% voix)
              </span>
            ))}
          </div>

          {/* Comparison table */}
          <div style={{ fontSize: '0.78rem' }}>
            <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border">
              <thead className="table-light">
                <tr>
                  <th>{t('multiwinner.method')}</th>
                  {names.map((n) => (
                    <th key={n} className="text-center">
                      {n}
                    </th>
                  ))}
                  <th className="text-center">{t('multiwinner.distortion')}</th>
                </tr>
                {/* Proportional reference row */}
                <tr style={{ background: '#f8f9fa', fontStyle: 'italic' }}>
                  <td style={{ fontSize: '0.7rem', color: '#6c757d' }}>
                    {t('multiwinner.proportional')}
                  </td>
                  {names.map((n) => (
                    <td key={n} className="text-center" style={{ color: '#6c757d' }}>
                      {data.proportional_reference[n] ?? 0}
                    </td>
                  ))}
                  <td className="text-center" style={{ color: '#6c757d' }}>
                    —
                  </td>
                </tr>
              </thead>
              <tbody>
                {METHOD_ORDER.map((m) => {
                  const md = data.methods[m];
                  return (
                    <tr key={m} style={{ fontWeight: m === data.best_method ? 600 : undefined }}>
                      <td>
                        {METHOD_LABELS[m]}
                        {m === data.best_method && (
                          <Badge variant="success" className="ms-1" style={{ fontSize: '0.6rem' }}>
                            {t('multiwinner.mostPR')}
                          </Badge>
                        )}
                      </td>
                      {names.map((n) => {
                        const sv = md?.seat_vs_votes[n];
                        return (
                          <td
                            key={n}
                            className="text-center"
                            style={sv ? deltaColor(sv.delta) : {}}
                          >
                            {md?.seats[n] ?? 0}
                            {sv && Math.abs(sv.delta) > 0.02 && (
                              <span style={{ fontSize: '0.65rem', marginLeft: 2 }}>
                                ({sv.delta > 0 ? '+' : ''}
                                {Math.round(sv.delta * 100)}pp)
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td className="text-center">
                        <Badge
                          variant={
                            md?.distortion > 0.1
                              ? 'danger'
                              : md?.distortion > 0.05
                                ? 'warning'
                                : 'success'
                          }
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

          <div className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
            {t('multiwinner.tableHint')}
          </div>
        </>
      )}
    </div>
  );
};

export default MultiwinnerCompare;
