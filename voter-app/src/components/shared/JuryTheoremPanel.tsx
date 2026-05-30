/**
 * JuryTheoremPanel — Condorcet Jury Theorem visualisation.
 *
 * Two charts:
 *   A) Competence curve: how collective accuracy grows as individual
 *      competence rises (0.51→0.99), one line per method + theoretical.
 *   B) Bar chart: current-parameter accuracy per method vs theoretical.
 *
 * Debounced competence slider triggers a new simulation call.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { apiPath } from '../../api/apiVersion';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  ReferenceLine, ResponsiveContainer, Cell, CartesianGrid,
} from 'recharts';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface MethodResult {
  accuracy:       number;
  beats_majority: boolean;
  beats_theory:   boolean;
}

interface CurvePoint {
  competence:   number;
  theoretical:  number;
  plurality?:   number;
  borda?:       number;
  irv?:         number;
  approval?:    number;
  schulze?:     number;
}

interface JuryData {
  theoretical_accuracy: number;
  methods:              Record<string, MethodResult>;
  best_method:          string;
  worst_method:         string;
  voter_competence:     number;
  num_voters:           number;
  competence_curve:     CurvePoint[];
  pedagogical_note:     string;
  pedagogical_note_en:  string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const METHOD_COLORS: Record<string, string> = {
  plurality:   '#6c757d',
  borda:       '#005CAB',
  irv:         '#C8590A',
  approval:    '#007A33',
  schulze:     '#9b59b6',
  theoretical: '#dc3545',
};

const METHODS = ['plurality', 'borda', 'irv', 'approval', 'schulze'] as const;

// ── Main component ────────────────────────────────────────────────────────────

const JuryTheoremPanel: React.FC = () => {
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.startsWith('en') ? 'en' : 'fr';

  const [numVoters,       setNumVoters]       = useState(100);
  const [numOptions,      setNumOptions]      = useState(2);
  const [competence,      setCompetence]      = useState(0.70);
  const [numSimulations,  setNumSimulations]  = useState(200);

  const [data,    setData]    = useState<JuryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const run = useCallback(async (comp: number, voters: number, opts: number, sims: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/jury')}`, {
        num_voters:            voters,
        num_options:           opts,
        correct_option_index:  0,
        voter_competence:      comp,
        num_simulations:       sims,
        seed:                  42,
      });
      setData(res.data);
    } catch {
      setError(t('jury.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  // Debounced competence change
  const handleCompetenceChange = (v: number) => {
    setCompetence(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(v, numVoters, numOptions, numSimulations), DEBOUNCE_MS);
  };

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  // ── Bar chart data ─────────────────────────────────────────────────────
  const barData = data
    ? METHODS.map((m) => ({
        name:        m,
        accuracy:    Math.round((data.methods[m]?.accuracy ?? 0) * 100),
        beats:       data.methods[m]?.beats_theory ?? false,
      })).sort((a, b) => b.accuracy - a.accuracy)
    : [];

  const theoryPct = data ? Math.round(data.theoretical_accuracy * 100) : 0;

  // ── Competence curve data (from precomputed curve) ─────────────────────
  const curveData: CurvePoint[] = data?.competence_curve ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">
            {t('jury.numVoters')}: <strong>{numVoters}</strong>
          </Form.Label>
          <Form.Range min={10} max={500} step={10} value={numVoters}
            onChange={e => setNumVoters(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">
            {t('jury.numOptions')}: <strong>{numOptions}</strong>
          </Form.Label>
          <Form.Range min={2} max={5} step={1} value={numOptions}
            onChange={e => setNumOptions(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={3}>
          <Form.Label className="small mb-0">
            {t('jury.numSims')}: <strong>{numSimulations}</strong>
          </Form.Label>
          <Form.Range min={50} max={500} step={50} value={numSimulations}
            onChange={e => setNumSimulations(Number(e.target.value))} />
        </Col>
        <Col xs={12} sm={3}>
          <Button variant="primary" className="w-100"
            onClick={() => run(competence, numVoters, numOptions, numSimulations)}
            disabled={loading}>
            {loading
              ? <><Spinner size="sm" className="me-1" />{t('jury.simulating')}</>
              : `⚖️ ${t('jury.run')}`}
          </Button>
        </Col>
      </Row>

      {/* Competence slider — debounced */}
      <div className="mb-3 border rounded p-3">
        <Form.Label className="fw-semibold mb-0" style={{ fontSize: '0.88rem' }}>
          {t('jury.competenceSlider')}: <strong>{Math.round(competence * 100)}%</strong>
          {loading && <Spinner size="sm" className="ms-2" />}
        </Form.Label>
        <Form.Range
          min={0.51} max={0.99} step={0.01} value={competence}
          onChange={e => handleCompetenceChange(Number(e.target.value))}
          data-testid="competence-slider"
        />
        <div className="d-flex justify-content-between"
          style={{ fontSize: '0.72rem', color: '#6c757d', marginTop: -4 }}>
          <span>0.51 ({t('jury.random')})</span>
          <span>1.0 ({t('jury.perfect')})</span>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('jury.prompt')}</Alert>}

      {data && (
        <>
          {/* Summary badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg="danger" data-testid="theory-badge">
              {t('jury.theory')}: {theoryPct}%
            </Badge>
            <Badge
              style={{ background: METHOD_COLORS[data.best_method] }}
              data-testid="best-method-badge"
            >
              🏆 {data.best_method}: {Math.round((data.methods[data.best_method]?.accuracy ?? 0) * 100)}%
            </Badge>
            <Badge bg="secondary">
              ↓ {data.worst_method}: {Math.round((data.methods[data.worst_method]?.accuracy ?? 0) * 100)}%
            </Badge>
          </div>

          {/* Pedagogical note */}
          <Alert variant="info" className="py-2 mb-3" style={{ fontSize: '0.84rem' }}
            data-testid="pedagogical-note">
            {lang === 'en' ? data.pedagogical_note_en : data.pedagogical_note}
          </Alert>

          <Row className="g-3">
            {/* A) Competence curve */}
            <Col xs={12} lg={7}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('jury.curveTitleLine')}
              </div>
              <div style={{ height: 260 }} data-testid="competence-curve-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={curveData} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                    <XAxis
                      dataKey="competence"
                      tickFormatter={v => `${Math.round(v * 100)}%`}
                      tick={{ fontSize: 10 }}
                      label={{ value: t('jury.axisCompetence'), position: 'insideBottom', offset: -12, fontSize: 10 }}
                    />
                    <YAxis
                      domain={[0.4, 1]}
                      tickFormatter={v => `${Math.round(v * 100)}%`}
                      tick={{ fontSize: 10 }}
                      width={40}
                    />
                    <Tooltip
                      formatter={(v: number, name: string) => [`${Math.round(v * 100)}%`, name]}
                      labelFormatter={v => `P = ${(Number(v)).toFixed(2)}`}
                    />
                    <Legend wrapperStyle={{ fontSize: '0.72rem' }} />
                    {/* Theoretical line */}
                    <Line
                      type="monotone" dataKey="theoretical" name={t('jury.theoretical')}
                      stroke={METHOD_COLORS.theoretical} strokeWidth={2}
                      strokeDasharray="6 3" dot={false} isAnimationActive={false}
                    />
                    {/* Current competence reference */}
                    <ReferenceLine
                      x={competence}
                      stroke="#adb5bd" strokeDasharray="3 2"
                      label={{ value: `P=${Math.round(competence * 100)}%`, fontSize: 9, fill: '#6c757d' }}
                    />
                    {/* Method lines */}
                    {METHODS.map((m) => (
                      <Line
                        key={m} type="monotone" dataKey={m} name={m}
                        stroke={METHOD_COLORS[m]} strokeWidth={1.5}
                        dot={false} isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Col>

            {/* B) Bar chart — current accuracy */}
            <Col xs={12} lg={5}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('jury.barTitle')} (P={Math.round(competence * 100)}%)
              </div>
              <div style={{ height: 260 }} data-testid="accuracy-bar-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={barData} layout="vertical"
                    margin={{ top: 4, right: 60, bottom: 4, left: 60 }}
                  >
                    <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 9 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={58} />
                    <Tooltip formatter={(v: number) => `${v}%`} />
                    <ReferenceLine x={theoryPct} stroke={METHOD_COLORS.theoretical}
                      strokeDasharray="4 2"
                      label={{ value: `${t('jury.theory')} ${theoryPct}%`, fontSize: 8, fill: '#dc3545', position: 'top' }}
                    />
                    <Bar dataKey="accuracy" radius={[0, 3, 3, 0]} isAnimationActive={false}>
                      {barData.map((entry, i) => (
                        <Cell
                          key={i}
                          fill={METHOD_COLORS[entry.name] ?? '#888'}
                          opacity={entry.beats ? 1.0 : 0.55}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#6c757d', marginTop: 4 }}>
                {t('jury.barHint')}
              </div>
            </Col>
          </Row>

          {/* Method table */}
          <div className="mt-3" style={{ fontSize: '0.8rem' }}>
            <div className="d-flex flex-wrap gap-2">
              {METHODS.map((m) => {
                const md = data.methods[m];
                if (!md) return null;
                const acc = Math.round(md.accuracy * 100);
                const delta = acc - theoryPct;
                return (
                  <Badge
                    key={m}
                    style={{
                      background: METHOD_COLORS[m],
                      opacity: md.beats_theory ? 1 : 0.65,
                      fontSize: '0.72rem',
                    }}
                    data-testid={`method-badge-${m}`}
                  >
                    {m}: {acc}%
                    {delta >= 0 ? ` (+${delta})` : ` (${delta})`}
                  </Badge>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default JuryTheoremPanel;
