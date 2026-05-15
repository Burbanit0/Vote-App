import React, { useMemo, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Container, Row, Table,
} from 'react-bootstrap';
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import regimes, {
  BlankVoteRegime, BlankVoteStatus, filterByImpact, sortByBlankRate,
} from '../data/blankVoteRegimes';
import { useMetaTags } from '../hooks/useMetaTags';
import ResponsiveTable from '../components/shared/ResponsiveTable';

// ── Status metadata ───────────────────────────────────────────────────────────

const STATUS_META: Record<BlankVoteStatus, { label: string; color: string; desc: string }> = {
  counted_separate: {
    label: 'Compté séparément',
    color: '#1a56cc',
    desc: 'Comptabilisé officiellement séparé des bulletins nuls',
  },
  symbolic: {
    label: 'Symbolique',
    color: '#006957',
    desc: 'Comptabilisé, poids politique mais pas d\'effet procédural',
  },
  competitive: {
    label: 'Compétitif',
    color: '#b71c1c',
    desc: 'Peut gagner l\'élection comme un candidat',
  },
  threshold: {
    label: 'Seuil constitutionnel',
    color: '#b35c00',
    desc: 'Déclenche une procédure spéciale si un seuil est dépassé',
  },
  merged_invalid: {
    label: 'Fusionné avec les nuls',
    color: '#6c757d',
    desc: 'Non distingué des bulletins invalides dans le décompte',
  },
};

// ── SVG Map ───────────────────────────────────────────────────────────────────
// Simplified bubble map: circles at approximate geographic centroids.
// Projection: x = (lon + 180) / 360 × W,  y = (90 − lat) / 180 × H

const MAP_W = 760;
const MAP_H = 380;

function toSvg(lat: number, lon: number): { x: number; y: number } {
  return {
    x: Math.round(((lon + 180) / 360) * MAP_W),
    y: Math.round(((90 - lat) / 180) * MAP_H),
  };
}

// Very simplified continent polygons (rough outlines for visual context)
const CONTINENT_PATHS = [
  // Europe
  { d: 'M 350,58 L 490,58 L 490,195 L 415,205 L 380,185 L 350,195 Z', fill: '#eef0e8' },
  // Africa
  { d: 'M 355,195 L 475,195 L 470,385 L 365,385 Z', fill: '#eef0e8' },
  // North America
  { d: 'M 70,50 L 280,50 L 275,200 L 200,230 L 100,200 L 70,160 Z', fill: '#eef0e8' },
  // South America
  { d: 'M 170,200 L 290,200 L 290,390 L 195,390 Z', fill: '#eef0e8' },
  // Asia
  { d: 'M 490,55 L 760,55 L 760,320 L 490,250 Z', fill: '#eef0e8' },
  // Oceania
  { d: 'M 628,255 L 780,255 L 780,390 L 628,390 Z', fill: '#eef0e8' },
];

interface MapProps {
  data: BlankVoteRegime[];
  highlighted?: string;
  onHover: (country: string | null) => void;
}

const BubbleMap: React.FC<MapProps> = ({ data, highlighted, onHover }) => (
  <svg
    viewBox={`0 0 ${MAP_W} ${MAP_H}`}
    style={{ width: '100%', height: 'auto', borderRadius: 8, border: '1px solid #dee2e6' }}
    role="img"
    aria-label="Carte des régimes du vote blanc dans le monde"
  >
    {/* Ocean */}
    <rect width={MAP_W} height={MAP_H} fill="#dbeafe" rx={8} />

    {/* Continents */}
    {CONTINENT_PATHS.map((p, i) => (
      <path key={i} d={p.d} fill={p.fill} stroke="#c9d1d9" strokeWidth={0.8} />
    ))}

    {/* Country bubbles */}
    {data.map((r) => {
      const { x, y } = toSvg(r.lat, r.lon);
      const col = STATUS_META[r.legal_status].color;
      const isHl = highlighted === r.country;
      return (
        <g
          key={r.country}
          style={{ cursor: 'pointer' }}
          onMouseEnter={() => onHover(r.country)}
          onMouseLeave={() => onHover(null)}
          role="button"
          aria-label={`${r.country} : ${STATUS_META[r.legal_status].label}`}
        >
          <circle
            cx={x}
            cy={y}
            r={isHl ? 14 : 11}
            fill={col}
            opacity={isHl ? 1 : 0.82}
            stroke="white"
            strokeWidth={isHl ? 2.5 : 1.5}
            style={{ transition: 'all 0.15s' }}
          />
          <text
            x={x}
            y={y + 4}
            textAnchor="middle"
            fontSize={isHl ? 11 : 9}
            fill="white"
            fontWeight={600}
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {r.blank_rate_typical.toFixed(1)}%
          </text>
          {/* Country label */}
          <text
            x={x}
            y={y + (isHl ? 28 : 24)}
            textAnchor="middle"
            fontSize={8}
            fill="#374151"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {r.flag}
          </text>
        </g>
      );
    })}

    {/* Tooltip-like highlight label */}
    {highlighted && (() => {
      const r = data.find((d) => d.country === highlighted);
      if (!r) return null;
      const { x, y } = toSvg(r.lat, r.lon);
      const boxX = Math.min(Math.max(x - 60, 4), MAP_W - 130);
      const boxY = y > MAP_H - 80 ? y - 58 : y + 20;
      return (
        <g style={{ pointerEvents: 'none' }}>
          <rect x={boxX} y={boxY} width={122} height={42} rx={6} fill="rgba(0,0,0,0.75)" />
          <text x={boxX + 61} y={boxY + 14} textAnchor="middle" fontSize={10} fill="white" fontWeight={700}>
            {r.flag} {r.country}
          </text>
          <text x={boxX + 61} y={boxY + 28} textAnchor="middle" fontSize={9} fill="#d1d5db">
            {STATUS_META[r.legal_status].label}
          </text>
          <text x={boxX + 61} y={boxY + 38} textAnchor="middle" fontSize={9} fill="#fbbf24">
            {r.blank_rate_typical}% en moy.
          </text>
        </g>
      );
    })()}
  </svg>
);

// ── Bar chart tooltip ─────────────────────────────────────────────────────────

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const r: BlankVoteRegime = payload[0].payload;
  return (
    <div style={{
      background: 'var(--bs-body-bg, white)',
      border: '1px solid var(--bs-border-color, #dee2e6)',
      borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    }}>
      <div className="fw-bold">{r.flag} {r.country}</div>
      <div style={{ color: STATUS_META[r.legal_status].color }}>
        {STATUS_META[r.legal_status].label}
      </div>
      <div>Taux typique : <strong>{r.blank_rate_typical} %</strong></div>
      {r.impact_on_result && (
        <div className="text-danger mt-1">⚠️ Peut modifier le résultat</div>
      )}
    </div>
  );
}

// ── InternationalRegimesPage ──────────────────────────────────────────────────

const InternationalRegimesPage: React.FC = () => {
  useMetaTags({
    title: 'Régimes internationaux du vote blanc — Vote Lab',
    description:
      'Comparaison de 15 pays : statut juridique, taux et impact constitutionnel du vote blanc.',
  });

  const [impactOnly,  setImpactOnly]  = useState(false);
  const [sortAsc,     setSortAsc]     = useState(false);
  const [highlighted, setHighlighted] = useState<string | null>(null);

  const displayed = useMemo(() => {
    const base = impactOnly ? filterByImpact(regimes) : regimes;
    return sortByBlankRate(base, sortAsc);
  }, [impactOnly, sortAsc]);

  const impactCount = regimes.filter((r) => r.impact_on_result).length;
  const total       = regimes.length;
  const avgRate     = regimes.reduce((s, r) => s + r.blank_rate_typical, 0) / total;

  const chartData = sortByBlankRate(regimes, true);

  return (
    <Container fluid className="py-4" style={{ maxWidth: 1300 }}>
      <h2 className="mb-1 fw-bold">🌍 Régimes internationaux du vote blanc</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
        Comparaison juridique de {total} pays : statut légal, taux de vote blanc,
        et impact constitutionnel sur le résultat de l'élection.
      </p>

      {/* ── Summary stats ── */}
      <Row className="g-3 mb-4">
        {[
          { value: total,             label: 'Pays analysés', color: '#1a56cc' },
          { value: impactCount,       label: 'Où le blanc compte', color: '#b35c00' },
          { value: `${avgRate.toFixed(1)} %`, label: 'Taux moyen', color: '#006957' },
          { value: 2,                 label: 'Peuvent invalider',   color: '#b71c1c' },
        ].map(({ value, label, color }) => (
          <Col xs={6} md={3} key={label}>
            <Card className="text-center h-100">
              <Card.Body className="py-3">
                <div style={{ fontSize: '2rem', fontWeight: 800, color }}>{value}</div>
                <div className="text-muted small mt-1">{label}</div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Row className="g-4">
        {/* ── Left: map + legend ── */}
        <Col lg={7}>
          <Card className="mb-3">
            <Card.Header className="d-flex align-items-center justify-content-between">
              <strong>Carte des régimes</strong>
              <span className="text-muted small">Passer la souris sur un pays pour les détails</span>
            </Card.Header>
            <Card.Body className="p-2">
              <BubbleMap
                data={regimes}
                highlighted={highlighted ?? undefined}
                onHover={setHighlighted}
              />
            </Card.Body>
          </Card>

          {/* Legend */}
          <Card>
            <Card.Header className="py-2"><strong>Légende</strong></Card.Header>
            <Card.Body className="py-2">
              <div className="d-flex flex-wrap gap-3">
                {(Object.entries(STATUS_META) as [BlankVoteStatus, typeof STATUS_META[BlankVoteStatus]][]).map(
                  ([key, { label, color, desc }]) => (
                    <div key={key} className="d-flex align-items-start gap-2">
                      <span
                        style={{
                          display: 'inline-block', width: 14, height: 14,
                          borderRadius: '50%', background: color, flexShrink: 0, marginTop: 2,
                        }}
                      />
                      <div>
                        <div className="fw-semibold" style={{ fontSize: '0.82rem', color }}>{label}</div>
                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>{desc}</div>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* ── Right: chart + table ── */}
        <Col lg={5}>
          {/* Bar chart */}
          <Card className="mb-3">
            <Card.Header><strong>Taux de vote blanc par pays</strong></Card.Header>
            <Card.Body className="p-2">
              <ResponsiveContainer width="100%" height={310}>
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ top: 4, right: 40, left: 4, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--bs-border-color, #dee2e6)" />
                  <XAxis
                    type="number"
                    domain={[0, 8]}
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="country"
                    width={80}
                    tick={({ x, y, payload }) => {
                      const r = regimes.find((d) => d.country === payload.value);
                      return (
                        <text x={x - 4} y={y + 4} textAnchor="end" fontSize={11} fill="var(--bs-body-color, #333)">
                          {r?.flag} {payload.value}
                        </text>
                      );
                    }}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="blank_rate_typical" radius={[0, 3, 3, 0]} maxBarSize={18}>
                    {chartData.map((entry) => (
                      <Cell
                        key={entry.country}
                        fill={STATUS_META[entry.legal_status].color}
                        opacity={entry.impact_on_result ? 1 : 0.75}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* ── Comparison table ── */}
      <Card className="mt-3 mb-4">
        <Card.Header className="d-flex align-items-center justify-content-between flex-wrap gap-2">
          <strong>Tableau comparatif</strong>
          <div className="d-flex gap-2">
            <Button
              variant={impactOnly ? 'warning' : 'outline-secondary'}
              size="sm"
              onClick={() => setImpactOnly((v) => !v)}
              aria-pressed={impactOnly}
            >
              {impactOnly ? '✓ ' : ''}Afficher seulement les pays où le blanc compte
            </Button>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => setSortAsc((v) => !v)}
              aria-label={sortAsc ? 'Trier décroissant' : 'Trier croissant'}
            >
              Taux {sortAsc ? '↑' : '↓'}
            </Button>
          </div>
        </Card.Header>
        <Card.Body className="p-0">
          <ResponsiveTable aria-label="Tableau comparatif des régimes du vote blanc">
            <Table bordered hover size="sm" className="mb-0" style={{ fontSize: '0.82rem' }}>
              <thead className="table-light">
                <tr>
                  <th>Pays</th>
                  <th>Statut juridique</th>
                  <th className="text-center">Taux typique</th>
                  <th className="text-center">Impact résultat</th>
                  <th>Depuis</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((r) => (
                  <tr
                    key={r.country}
                    style={r.impact_on_result ? { backgroundColor: '#fff8e1' } : undefined}
                    onMouseEnter={() => setHighlighted(r.country)}
                    onMouseLeave={() => setHighlighted(null)}
                  >
                    <td>
                      <span className="me-1">{r.flag}</span>
                      <strong>{r.country}</strong>
                    </td>
                    <td>
                      <Badge
                        style={{
                          background: STATUS_META[r.legal_status].color,
                          fontSize: '0.72rem',
                        }}
                      >
                        {STATUS_META[r.legal_status].label}
                      </Badge>
                    </td>
                    <td className="text-center fw-semibold">
                      {r.blank_rate_typical.toFixed(1)} %
                    </td>
                    <td className="text-center">
                      {r.impact_on_result
                        ? <span className="text-danger fw-bold">⚠️ Oui</span>
                        : <span className="text-muted">Non</span>}
                    </td>
                    <td className="text-muted">{r.since_year ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </ResponsiveTable>
        </Card.Body>
      </Card>

      {/* ── Conclusion ── */}
      <Alert variant="info" style={{ fontSize: '0.88rem', lineHeight: 1.7 }}>
        <strong>📊 Synthèse :</strong>{' '}
        Dans <strong>{impactCount} pays sur {total}</strong> analysés, le vote blanc peut
        modifier le résultat de l'élection — soit en agissant comme un candidat compétitif
        (Uruguay), soit en déclenchant une nouvelle élection si un seuil est dépassé
        (Colombie). Dans les {total - impactCount} autres pays, le vote blanc est reconnu
        symboliquement ou noyé dans les bulletins invalides, sans effet constitutionnel
        direct. Le taux moyen de vote blanc dans l'échantillon est de{' '}
        <strong>{avgRate.toFixed(1)} %</strong>,
        avec des pics notables en Colombie ({regimes.find((r) => r.country === 'Colombie')?.blank_rate_typical} %),
        Australie ({regimes.find((r) => r.country === 'Australie')?.blank_rate_typical} %),
        et Belgique ({regimes.find((r) => r.country === 'Belgique')?.blank_rate_typical} %).
      </Alert>

      <div className="text-muted small mt-1" style={{ fontSize: '0.75rem' }}>
        Sources : législations électorales nationales, commissions électorales officielles et
        littérature académique en droit électoral comparé. Données indicatives — mai 2026.
      </div>
    </Container>
  );
};

export default InternationalRegimesPage;
