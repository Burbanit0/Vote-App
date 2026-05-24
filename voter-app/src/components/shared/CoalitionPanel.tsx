import React, { useMemo, useState } from 'react';
import axios from 'axios';
import { apiPath } from '../../api/apiVersion';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Spinner, Table } from 'react-bootstrap';
import { useElection } from '../../context/ElectionContext';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';

// ── Types ─────────────────────────────────────────────────────────────────────

interface MethodResult {
  method: string;
  winner: string;
  seats: Record<string, number>;
  vote_shares: Record<string, number>;
  coalition_parties: string[];
  coalition_seats: number;
  coalition_spread: number;
  government_possible: boolean;
}

interface CoalitionData {
  methods: MethodResult[];
  candidates: { name: string; x: number }[];
  total_seats: number;
  seat_threshold: number;
  most_centrist_method: string | null;
  most_divergent_method: string | null;
  inter_method_agreement: number;
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
  coalition: string[];
  candidateNames: string[];
  totalSeats: number;
}

const Hémicycle: React.FC<HémicycleProps> = ({ seats, coalition, candidateNames, totalSeats }) => {
  const W = 320;
  const H = 175;
  const cx = W / 2;
  const cy = H - 10;
  const rInner = 55;
  const rOuter = 140;

  // Sort seats by candidate (left-to-right ideological order = insertion order)
  const parties = candidateNames.filter((n) => (seats[n] ?? 0) > 0);
  const total = totalSeats || 1;

  // Build arc segments
  const segments: { name: string; startAngle: number; endAngle: number }[] = [];
  let cumAngle = Math.PI; // start at left (180°)
  for (const name of parties) {
    const fraction = (seats[name] ?? 0) / total;
    const span = fraction * Math.PI; // half circle = PI radians
    segments.push({ name, startAngle: cumAngle, endAngle: cumAngle + span });
    cumAngle += span;
  }

  function polar(r: number, angle: number): [number, number] {
    return [cx + r * Math.cos(angle), cy - r * Math.sin(angle)];
  }

  function arcPath(r1: number, r2: number, a1: number, a2: number): string {
    const [x1, y1] = polar(r1, a1);
    const [x2, y2] = polar(r2, a1);
    const [x3, y3] = polar(r2, a2);
    const [x4, y4] = polar(r1, a2);
    const largeArc = a2 - a1 > Math.PI ? 1 : 0;
    return [
      `M ${x1} ${y1}`,
      `L ${x2} ${y2}`,
      `A ${r2} ${r2} 0 ${largeArc} 0 ${x3} ${y3}`,
      `L ${x4} ${y4}`,
      `A ${r1} ${r1} 0 ${largeArc} 1 ${x1} ${y1}`,
      'Z',
    ].join(' ');
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ maxWidth: 360, display: 'block', margin: '0 auto' }}
      role="img"
      aria-label="Hémicycle"
    >
      {segments.map(({ name, startAngle, endAngle }) => {
        const inCoalition = coalition.includes(name);
        const color = candidateColor(name, candidateNames);
        return (
          <path
            key={name}
            d={arcPath(rInner, rOuter, startAngle, endAngle)}
            fill={color}
            opacity={inCoalition ? 1 : 0.25}
            stroke="#fff"
            strokeWidth={1.5}
          >
            <title>{name}: {seats[name]} seats{inCoalition ? ' (coalition)' : ''}</title>
          </path>
        );
      })}

      {/* Coalition boundary outline */}
      {coalition.length > 0 && (() => {
        const coalSeg = segments.filter((s) => coalition.includes(s.name));
        if (!coalSeg.length) return null;
        const a1 = coalSeg[0].startAngle;
        const a2 = coalSeg[coalSeg.length - 1].endAngle;
        const [ox1, oy1] = polar(rInner, a1);
        const [ox2, oy2] = polar(rOuter, a1);
        const [ox3, oy3] = polar(rOuter, a2);
        const [ox4, oy4] = polar(rInner, a2);
        const la = a2 - a1 > Math.PI ? 1 : 0;
        return (
          <path
            d={`M${ox1} ${oy1} L${ox2} ${oy2} A${rOuter} ${rOuter} 0 ${la} 0 ${ox3} ${oy3} L${ox4} ${oy4} A${rInner} ${rInner} 0 ${la} 1 ${ox1} ${oy1} Z`}
            fill="none"
            stroke="#212529"
            strokeWidth={2}
            strokeDasharray="4 2"
          />
        );
      })()}

      {/* Majority line */}
      <line
        x1={polar(rInner - 4, Math.PI / 2)[0]}
        y1={polar(rInner - 4, Math.PI / 2)[1]}
        x2={polar(rOuter + 4, Math.PI / 2)[0]}
        y2={polar(rOuter + 4, Math.PI / 2)[1]}
        stroke="#dc3545"
        strokeWidth={2}
        strokeDasharray="3 2"
      />

      {/* Centre label */}
      <text x={cx} y={cy - rInner / 2 + 6} textAnchor="middle" fontSize={10} fill="#495057">
        50 %
      </text>
    </svg>
  );
};

// ── Spread bar ─────────────────────────────────────────────────────────────────

const SpreadBar: React.FC<{ value: number; max: number }> = ({ value, max }) => {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const hue = Math.round(120 - pct * 1.2); // green → red
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div
        style={{
          flex: 1, height: 8, background: '#e9ecef', borderRadius: 4, overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: `hsl(${hue},70%,45%)`,
            borderRadius: 4,
            transition: 'width 0.4s',
          }}
        />
      </div>
      <span style={{ fontSize: '0.75rem', minWidth: 36 }}>{value.toFixed(3)}</span>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const CoalitionPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();
  const [data, setData] = useState<CoalitionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null);

  const candidateNames = useMemo(
    () => config.candidates.map((c) => c.name),
    [config.candidates]
  );

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/coalition')}`, {
        candidates:           config.candidates,
        num_voters:           config.num_voters,
        ideology:             config.ideology,
        seed:                 config.seed,
        total_seats:          100,
        government_threshold: 0.5,
      });
      setData(res.data);
      setSelectedMethod(res.data.methods[0]?.method ?? null);
    } catch {
      setError(t('coalition.error'));
    } finally {
      setLoading(false);
    }
  }

  const selected = data?.methods.find((m) => m.method === selectedMethod) ?? data?.methods[0];
  const maxSpread = data
    ? Math.max(...data.methods.map((m) => m.coalition_spread), 0.01)
    : 1;

  if (!data) {
    return (
      <div className="text-center py-4">
        <p className="text-muted mb-3">{t('coalition.prompt')}</p>
        <Button variant="primary" onClick={run} disabled={loading}>
          {loading
            ? <><Spinner size="sm" className="me-2" />{t('coalition.computing')}</>
            : `🏛 ${t('coalition.run')}`}
        </Button>
        {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
        <div className="d-flex gap-2 flex-wrap">
          <Badge bg="primary">
            {t('coalition.totalSeats')}: {data.total_seats}
          </Badge>
          <Badge bg="secondary">
            {t('coalition.threshold')}: {data.seat_threshold}
          </Badge>
          {data.most_centrist_method && (
            <Badge bg="success">
              {t('coalition.mostCentrist')}: {data.most_centrist_method}
            </Badge>
          )}
          {data.most_divergent_method && (
            <Badge bg="warning" text="dark">
              {t('coalition.mostDivergent')}: {data.most_divergent_method}
            </Badge>
          )}
        </div>
        <Button variant="outline-secondary" size="sm" onClick={run} disabled={loading}>
          {loading ? <Spinner size="sm" /> : '↺'}
        </Button>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {/* Pedagogical message */}
      <Alert variant="info" className="py-2 mb-3" style={{ fontSize: '0.84rem' }}>
        {data.most_centrist_method && data.most_divergent_method
          ? t('coalition.pedagogical', {
              centrist:  data.most_centrist_method,
              divergent: data.most_divergent_method,
            })
          : t('coalition.pedagogicalDefault')}
      </Alert>

      <div className="row g-3">
        {/* Left: method selector table */}
        <div className="col-12 col-lg-5">
          <Table bordered hover size="sm" style={{ fontSize: '0.8rem' }}>
            <thead className="table-light">
              <tr>
                <th>{t('common.method')}</th>
                <th>{t('coalition.coalitionParties')}</th>
                <th>{t('coalition.spread')}</th>
                <th>{t('coalition.possible')}</th>
              </tr>
            </thead>
            <tbody>
              {data.methods.map((m) => (
                <tr
                  key={m.method}
                  onClick={() => setSelectedMethod(m.method)}
                  style={{
                    cursor: 'pointer',
                    background: selectedMethod === m.method ? 'var(--bs-primary-bg-subtle)' : '',
                  }}
                >
                  <td className="fw-semibold" style={{ fontSize: '0.75rem' }}>{m.method}</td>
                  <td>
                    {m.coalition_parties.map((p) => (
                      <span
                        key={p}
                        className="badge me-1"
                        style={{ background: candidateColor(p, candidateNames), fontSize: '0.7rem' }}
                      >
                        {p}
                      </span>
                    ))}
                  </td>
                  <td style={{ minWidth: 90 }}>
                    <SpreadBar value={m.coalition_spread} max={maxSpread} />
                  </td>
                  <td className="text-center">
                    {m.government_possible
                      ? <span style={{ color: '#007A33' }}>✓</span>
                      : <span style={{ color: '#dc3545' }}>✗</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>

        {/* Right: hémicycle for selected method */}
        {selected && (
          <div className="col-12 col-lg-7">
            <div
              className="border rounded p-3"
              style={{ background: 'var(--bs-body-bg)' }}
            >
              <div className="text-center mb-2" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                {selected.method}
                {' — '}
                {selected.government_possible
                  ? <span className="text-success">{t('coalition.governmentPossible')}</span>
                  : <span className="text-danger">{t('coalition.governmentImpossible')}</span>}
              </div>

              <Hémicycle
                seats={selected.seats}
                coalition={selected.coalition_parties}
                candidateNames={candidateNames}
                totalSeats={data.total_seats}
              />

              {/* Legend */}
              <div className="d-flex flex-wrap gap-2 justify-content-center mt-2">
                {candidateNames.map((name) => (
                  <div key={name} className="d-flex align-items-center gap-1" style={{ fontSize: '0.78rem' }}>
                    <div
                      style={{
                        width: 12, height: 12, borderRadius: 2,
                        background: candidateColor(name, candidateNames),
                        opacity: selected.coalition_parties.includes(name) ? 1 : 0.3,
                      }}
                    />
                    <span style={{ opacity: selected.coalition_parties.includes(name) ? 1 : 0.5 }}>
                      {name} ({selected.seats[name] ?? 0})
                    </span>
                  </div>
                ))}
              </div>

              {/* Seat breakdown */}
              <div className="mt-3" style={{ fontSize: '0.8rem' }}>
                <strong>{t('coalition.seatBreakdown')}</strong>
                <div className="d-flex flex-wrap gap-2 mt-1">
                  {selected.coalition_parties.map((p) => (
                    <Badge key={p} style={{ background: candidateColor(p, candidateNames) }}>
                      {p}: {selected.seats[p] ?? 0} {t('coalition.seats')}
                    </Badge>
                  ))}
                </div>
                <div className="mt-1 text-muted">
                  {t('coalition.total')}: {selected.coalition_seats} / {data.seat_threshold} {t('coalition.required')}
                </div>
                <div className="mt-1">
                  {t('coalition.spread')}: <strong>{selected.coalition_spread.toFixed(3)}</strong>
                  {' '}
                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                    ({t('coalition.spreadHint')})
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CoalitionPanel;
