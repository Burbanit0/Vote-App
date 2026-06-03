import React, { useCallback, useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Range, Select } from '@/components/ui/form-controls';
import { Col, Container, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  CartesianGrid,
  Dot,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMetaTags } from '../hooks/useMetaTags';
import { runWhatIf, VariantParam, WhatIfDataPoint } from '../services/whatIfApi';
import { CHART_COLORS_LIGHT } from '../constants/chartColors';
import { METHOD_LABELS } from '../components/Simulation/simulationConstants';
import { useExpertMode } from '../stores/useUIStore';

// ── Constants ──────────────────────────────────────────────────────────────

const SHOWN_METHODS = ['plurality', 'borda', 'irv', 'schulze', 'approval'] as const;

const VARIANT_PARAMS: { value: VariantParam; label: string; unit: string; min: number; max: number; step: number; defaultMin: number; defaultMax: number }[] = [
  { value: 'num_voters',     label: "Nombre d'électeurs",   unit: 'électeurs',  min: 100,  max: 10000, step: 100,  defaultMin: 200,   defaultMax: 5000 },
  { value: 'num_candidates', label: 'Nombre de candidats',  unit: 'candidats',  min: 2,    max: 8,     step: 1,    defaultMin: 2,     defaultMax: 8    },
  { value: 'blank_pct',      label: 'Vote blanc (%)',        unit: '%',          min: 0,    max: 0.5,   step: 0.05, defaultMin: 0,     defaultMax: 0.40 },
  { value: 'polarization',   label: 'Polarisation',          unit: 'indice',     min: 0.1,  max: 2.0,   step: 0.1,  defaultMin: 0.2,   defaultMax: 2.0  },
];

const IDEOLOGY_OPTIONS = [
  { value: 'random',      label: 'Aléatoire' },
  { value: 'centrist',    label: 'Centriste' },
  { value: 'polarized',   label: 'Polarisé' },
  { value: 'left_skewed', label: 'Gauche' },
  { value: 'right_skewed',label: 'Droite' },
];

const N_POINTS = 6;
const METHOD_COLORS: Record<string, string> = Object.fromEntries(
  SHOWN_METHODS.map((m, i) => [m, CHART_COLORS_LIGHT[i % CHART_COLORS_LIGHT.length]])
);

// ── Helper: generate evenly-spaced values ──────────────────────────────────

export function generateValues(min: number, max: number, n: number): number[] {
  if (n <= 1) return [min];
  return Array.from({ length: n }, (_, i) => {
    const v = min + (max - min) * (i / (n - 1));
    // Round to avoid floating-point noise
    return Math.round(v * 1000) / 1000;
  });
}

// ── Helper: detect winner changes ─────────────────────────────────────────

export interface WinnerChange {
  method: string;
  valueIndex: number;
  value: number;
  from: string | null;
  to: string | null;
}

export function detectWinnerChanges(
  results: WhatIfDataPoint[],
  methods: readonly string[],
): WinnerChange[] {
  const changes: WinnerChange[] = [];
  for (const method of methods) {
    for (let i = 1; i < results.length; i++) {
      const prev = results[i - 1].methods[method]?.winner ?? null;
      const curr = results[i].methods[method]?.winner ?? null;
      if (prev !== curr) {
        changes.push({ method, valueIndex: i, value: results[i].value, from: prev, to: curr });
      }
    }
  }
  return changes;
}

// ── Helper: build divergence message ──────────────────────────────────────

function buildDivergenceMessage(
  results: WhatIfDataPoint[],
  variantLabel: string,
  variantUnit: string,
): string | null {
  if (!results.length) return null;

  // Find a data point where methods disagree
  const divergent = results.find((r) => {
    const winners = SHOWN_METHODS.map((m) => r.methods[m]?.winner).filter(Boolean);
    return new Set(winners).size > 1;
  });

  if (!divergent) return null;

  const winnerMap: Record<string, string[]> = {};
  for (const m of SHOWN_METHODS) {
    const w = divergent.methods[m]?.winner;
    if (w) {
      winnerMap[w] = [...(winnerMap[w] ?? []), METHOD_LABELS[m] ?? m];
    }
  }

  const parts = Object.entries(winnerMap).map(([w, ms]) => `${ms.join(' et ')} → ${w}`);
  const valueStr = variantUnit === '%'
    ? `${(divergent.value * 100).toFixed(0)} %`
    : `${divergent.value}`;

  return `Pour ${variantLabel.toLowerCase()} = ${valueStr} : ${parts.join(' / ')}`;
}

// ── Custom dot: highlights winner changes ─────────────────────────────────

function WinnerChangeDot(props: any) {
  const { cx, cy, payload, method, results } = props;
  if (!cx || !cy || !payload) return null;
  const idx = results.findIndex((r: WhatIfDataPoint) => r.value === payload.value);
  if (idx <= 0) return <Dot {...props} r={3} />;
  const prev = results[idx - 1].methods[method]?.winner;
  const curr = results[idx].methods[method]?.winner;
  const changed = prev && curr && prev !== curr;
  return <Dot {...props} r={changed ? 7 : 3} fill={changed ? '#f59e0b' : props.fill} stroke={changed ? '#b45309' : props.stroke} />;
}

// ── Custom tooltip ────────────────────────────────────────────────────────

function WhatIfTooltip({ active, payload, label, variantUnit, results }: any) {
  if (!active || !payload?.length) return null;
  const labelStr = variantUnit === '%' ? `${(Number(label) * 100).toFixed(0)} %` : `${label}`;
  const r = results.find((d: WhatIfDataPoint) => d.value === Number(label));
  return (
    <div
      style={{
        background: 'var(--bs-body-bg, white)',
        border: '1px solid var(--bs-border-color, #dee2e6)',
        borderRadius: 8, padding: '10px 14px', fontSize: '0.82rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      <div className="fw-bold mb-1">{labelStr}</div>
      {payload.map((entry: any) => {
        const methodKey = entry.dataKey?.replace('_score', '');
        const winner = r?.methods[methodKey]?.winner ?? '—';
        return (
          <div key={methodKey} style={{ color: entry.color }} className="d-flex justify-content-between gap-3">
            <span>{METHOD_LABELS[methodKey] ?? methodKey}</span>
            <span className="fw-semibold">{entry.value != null ? `${entry.value} %` : '—'} · {winner}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── WhatIfPage ────────────────────────────────────────────────────────────

const WhatIfPage: React.FC = () => {
  useMetaTags({
    title: 'Et si… — Analyse comparative — Vote Lab',
    description: 'Variez un paramètre électoral et observez comment les méthodes de vote changent de vainqueur.',
  });

  const { expertMode } = useExpertMode();

  // ── Base config ──
  const [numCandidates, setNumCandidates] = useState(4);
  const [numVoters,     setNumVoters]     = useState(500);
  const [ideoDistrib,   setIdeoDistrib]   = useState('random');

  // ── Variant config ──
  const [variantParam,  setVariantParam]  = useState<VariantParam>('num_voters');
  const [variantMin,    setVariantMin]    = useState(200);
  const [variantMax,    setVariantMax]    = useState(5000);

  const paramDef = useMemo(
    () => VARIANT_PARAMS.find((p) => p.value === variantParam)!,
    [variantParam],
  );

  const variantValues = useMemo(
    () => generateValues(variantMin, variantMax, N_POINTS),
    [variantMin, variantMax],
  );

  // ── Results ──
  const [results,  setResults]  = useState<WhatIfDataPoint[]>([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  // ── Chart data ──
  const chartData = useMemo(() =>
    results.map((r) => ({
      value: r.value,
      ...Object.fromEntries(
        SHOWN_METHODS.map((m) => [`${m}_score`, r.methods[m]?.score ?? null])
      ),
    })),
    [results],
  );

  const winnerChanges = useMemo(
    () => detectWinnerChanges(results, SHOWN_METHODS),
    [results],
  );

  const changeValueIndices = useMemo(
    () => new Set(winnerChanges.map((c) => c.value)),
    [winnerChanges],
  );

  const divergenceMsg = useMemo(
    () => buildDivergenceMessage(results, paramDef.label, paramDef.unit),
    [results, paramDef],
  );

  // ── Handle variant param change ──
  const handleVariantParamChange = useCallback((p: VariantParam) => {
    const def = VARIANT_PARAMS.find((d) => d.value === p)!;
    setVariantParam(p);
    setVariantMin(def.defaultMin);
    setVariantMax(def.defaultMax);
    setResults([]);
    setError(null);
  }, []);

  // ── Run analysis ──
  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await runWhatIf({
        base: { num_candidates: numCandidates, num_voters: numVoters, ideology_distribution: ideoDistrib },
        variant_param: variantParam,
        variant_values: variantValues,
      });
      setResults(resp.results);
    } catch (e: any) {
      setError(e?.response?.data?.error ?? e?.message ?? 'Erreur lors de l\'analyse');
    } finally {
      setLoading(false);
    }
  }, [numCandidates, numVoters, ideoDistrib, variantParam, variantValues]);

  // ── X-axis label formatter ──
  const xFormatter = useCallback(
    (v: number) => paramDef.unit === '%' ? `${(v * 100).toFixed(0)}%` : String(v),
    [paramDef],
  );

  const hasResults = results.length > 0;

  return (
    <Container className="py-4" style={{ maxWidth: 1100 }}>
      <h2 className="mb-1 fw-bold">Et si…</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.95rem' }}>
        Faites varier un seul paramètre et observez comment chaque méthode de vote change de vainqueur.
      </p>

      <Row className="g-4 mb-4">
        {/* ── Left column — base config ── */}
        <Col md={5}>
          <Card className="h-100">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 fw-semibold">⚙️ Scénario de base</CardHeader>
            <CardBody>
              {/* num_candidates */}
              <div className="mb-3">
                <label htmlFor="wi-num-cand" className="mb-1 inline-block small mb-1">
                  Candidats : <strong>{numCandidates}</strong>
                </label>
                <Range
                  id="wi-num-cand"
                  min={2} max={8} step={1}
                  value={numCandidates}
                  onChange={(e) => setNumCandidates(Number(e.target.value))}
                  aria-valuemin={2} aria-valuemax={8} aria-valuenow={numCandidates}
                  disabled={variantParam === 'num_candidates'}
                />
                {variantParam === 'num_candidates' && (
                  <small className="block text-sm text-muted-foreground">Paramètre en cours de variation — slider désactivé</small>
                )}
              </div>

              {/* num_voters */}
              <div className="mb-3">
                <label htmlFor="wi-num-voters" className="mb-1 inline-block small mb-1">
                  Électeurs : <strong>{numVoters.toLocaleString()}</strong>
                </label>
                <Range
                  id="wi-num-voters"
                  min={100} max={3000} step={100}
                  value={numVoters}
                  onChange={(e) => setNumVoters(Number(e.target.value))}
                  aria-valuemin={100} aria-valuemax={3000} aria-valuenow={numVoters}
                  disabled={variantParam === 'num_voters'}
                />
                {variantParam === 'num_voters' && (
                  <small className="block text-sm text-muted-foreground">Paramètre en cours de variation — slider désactivé</small>
                )}
              </div>

              {/* ideology_distribution */}
              <div className="mb-0">
                <label htmlFor="wi-ideo" className="mb-1 inline-block small mb-1">
                  Distribution idéologique
                </label>
                <Select
                  id="wi-ideo"
                  size="sm"
                  value={ideoDistrib}
                  onChange={(e) => setIdeoDistrib(e.target.value)}
                  disabled={variantParam === 'polarization'}
                >
                  {IDEOLOGY_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </Select>
                {variantParam === 'polarization' && (
                  <small className="block text-sm text-muted-foreground">La polarisation varie automatiquement</small>
                )}
              </div>
            </CardBody>
          </Card>
        </Col>

        {/* ── Right column — variant config ── */}
        <Col md={7}>
          <Card className="h-100">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 fw-semibold">🔀 Paramètre variable</CardHeader>
            <CardBody>
              {/* Variant param selector */}
              <div className="d-flex gap-2 flex-wrap mb-4" role="group" aria-label="Paramètre à faire varier">
                {VARIANT_PARAMS.map((p) => (
                  <Button
                    key={p.value}
                    size="sm"
                    variant={variantParam === p.value ? 'primary' : 'outline-secondary'}
                    onClick={() => handleVariantParamChange(p.value)}
                    aria-pressed={variantParam === p.value}
                  >
                    {p.label}
                  </Button>
                ))}
              </div>

              {/* Min / Max sliders */}
              <Row className="g-3 mb-3">
                <Col md={6}>
                  <div>
                    <label htmlFor="wi-var-min" className="mb-1 inline-block small mb-1">
                      Valeur min : <strong>
                        {paramDef.unit === '%' ? `${(variantMin * 100).toFixed(0)} %` : variantMin}
                      </strong>
                    </label>
                    <Range
                      id="wi-var-min"
                      min={paramDef.min} max={paramDef.max} step={paramDef.step}
                      value={variantMin}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setVariantMin(v);
                        if (v >= variantMax) setVariantMax(Math.min(paramDef.max, v + paramDef.step * 3));
                      }}
                    />
                  </div>
                </Col>
                <Col md={6}>
                  <div>
                    <label htmlFor="wi-var-max" className="mb-1 inline-block small mb-1">
                      Valeur max : <strong>
                        {paramDef.unit === '%' ? `${(variantMax * 100).toFixed(0)} %` : variantMax}
                      </strong>
                    </label>
                    <Range
                      id="wi-var-max"
                      min={paramDef.min} max={paramDef.max} step={paramDef.step}
                      value={variantMax}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setVariantMax(v);
                        if (v <= variantMin) setVariantMin(Math.max(paramDef.min, v - paramDef.step * 3));
                      }}
                    />
                  </div>
                </Col>
              </Row>

              {/* Values preview */}
              <div className="mb-3">
                <small className="text-muted">
                  Valeurs testées ({N_POINTS}) :{' '}
                  {variantValues.map((v) =>
                    paramDef.unit === '%' ? `${(v * 100).toFixed(0)}%` : v
                  ).join(' · ')}
                </small>
              </div>

              {/* Run button */}
              <Button
                variant="primary"
                className="w-100"
                onClick={runAnalysis}
                disabled={loading}
              >
                {loading ? (
                  <><Spinner size="sm" className="me-2" />Analyse en cours…</>
                ) : '▶ Lancer l\'analyse Et si…'}
              </Button>
            </CardBody>
          </Card>
        </Col>
      </Row>

      {/* ── Error ── */}
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      {/* ── Results chart ── */}
      {hasResults && (
        <>
          <Card className="mb-3">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 d-flex align-items-center justify-content-between">
              <strong>Score de majorité par méthode</strong>
              <small className="text-muted">
                {paramDef.label} varie de {xFormatter(variantMin)} à {xFormatter(variantMax)}
                {' · '}⭐ = changement de vainqueur
              </small>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--bs-border-color, #dee2e6)" />
                  <XAxis
                    dataKey="value"
                    tickFormatter={xFormatter}
                    label={{ value: paramDef.label, position: 'insideBottom', offset: -4, fontSize: 12 }}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    label={{ value: 'Score majorité (%)', angle: -90, position: 'insideLeft', fontSize: 12 }}
                    tick={{ fontSize: 11 }}
                    width={60}
                  />
                  <Tooltip
                    content={<WhatIfTooltip variantUnit={paramDef.unit} results={results} />}
                  />
                  <Legend verticalAlign="top" formatter={(value) => {
                    const m = String(value).replace('_score', '');
                    return METHOD_LABELS[m] ?? m;
                  }} />

                  {/* Reference lines where winner changes */}
                  {[...changeValueIndices].map((v) => (
                    <ReferenceLine
                      key={v}
                      x={v}
                      stroke="#f59e0b"
                      strokeDasharray="4 2"
                      strokeWidth={2}
                      label={{ value: '⭐', position: 'top', fontSize: 14 }}
                    />
                  ))}

                  {SHOWN_METHODS.map((method) => (
                    <Line
                      key={method}
                      type="monotone"
                      dataKey={`${method}_score`}
                      name={`${method}_score`}
                      stroke={METHOD_COLORS[method]}
                      strokeWidth={2}
                      dot={(props: any) => (
                        <WinnerChangeDot {...props} method={method} results={results} />
                      )}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* ── Divergence message ── */}
          {divergenceMsg && (
            <Alert variant="warning" className="mb-3" style={{ fontSize: '0.9rem' }}>
              <strong>⚠️ Divergence détectée :</strong> {divergenceMsg}
            </Alert>
          )}

          {/* ── Winner changes detail ── */}
          {winnerChanges.length > 0 && expertMode && (
            <Card className="mb-3">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2"><strong>Changements de vainqueur</strong></CardHeader>
              <CardBody className="py-2">
                {winnerChanges.map((c, i) => (
                  <div key={i} className="d-flex align-items-center gap-2 mb-1" style={{ fontSize: '0.85rem' }}>
                    <Badge variant="secondary">{METHOD_LABELS[c.method] ?? c.method}</Badge>
                    <span>{xFormatter(c.value)} →</span>
                    <span className="text-muted">{c.from ?? '—'}</span>
                    <span>→</span>
                    <span className="fw-semibold">{c.to ?? '—'}</span>
                  </div>
                ))}
              </CardBody>
            </Card>
          )}

          {/* ── Data table ── */}
          <div className="table-responsive mb-3">
            <table className="table table-sm table-bordered" style={{ fontSize: '0.82rem' }}>
              <thead className="table-light">
                <tr>
                  <th>{paramDef.label}</th>
                  {SHOWN_METHODS.map((m) => (
                    <th key={m} className="text-center">{METHOD_LABELS[m] ?? m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i}>
                    <td className="fw-semibold">{xFormatter(r.value)}</td>
                    {SHOWN_METHODS.map((m) => {
                      const md   = r.methods[m];
                      const prev = i > 0 ? results[i - 1].methods[m]?.winner : null;
                      const changed = prev !== null && prev !== md?.winner;
                      return (
                        <td
                          key={m}
                          className="text-center"
                          style={changed ? { backgroundColor: '#fef9c3' } : undefined}
                        >
                          {md?.winner ?? '—'}
                          {md?.score != null && (
                            <div style={{ fontSize: '0.75rem', color: '#6c757d' }}>{md.score}%</div>
                          )}
                          {changed && <span aria-hidden="true"> ⭐</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!hasResults && !loading && (
        <Alert variant="info">
          Configurez le scénario de base, choisissez le paramètre à faire varier, puis cliquez sur{' '}
          <strong>Lancer l'analyse</strong>.
        </Alert>
      )}
    </Container>
  );
};

export default WhatIfPage;
