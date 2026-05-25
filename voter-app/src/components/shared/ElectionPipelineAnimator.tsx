import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Row, Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import i18n from '../../i18n';
import axios from 'axios';
import { useElection } from '../../context/ElectionContext';
import MethodGroupDonut from './MethodGroupDonut';
import { apiPath } from '../../api/apiVersion';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4433';

// ── SVG constants (same coord system as IdeologyMapChart) ─────────────────────

const SVG_W   = 400;
const SVG_H   = 400;
const MARGIN  = 28;
const PLOT_W  = SVG_W - 2 * MARGIN;
const PLOT_H  = SVG_H - 2 * MARGIN;

function domainToSvg(v: number, axis: 'x' | 'y'): number {
  if (axis === 'x') return MARGIN + ((v + 1) / 2) * PLOT_W;
  return MARGIN + ((1 - v) / 2) * PLOT_H;
}

// ── Colours ───────────────────────────────────────────────────────────────────

const CAND_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#7B2D8B',
  '#9C3A00', '#005f73',
];
const BLANK_COLOR = '#adb5bd';
const PARTY_COLORS: Record<string, string> = {
  Green: '#007A33', Liberal: '#005CAB',
  Conservative: '#C8590A', Independent: '#6c757d',
};

// ── Step icon mapping ─────────────────────────────────────────────────────────

const STEP_ICONS: Record<string, string> = {
  base:        '👥',
  campaign:    '📅',
  contagion:   '🦠',
  information: '📡',
  results:     '🏆',
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoterSnap {
  id:         number;
  x:          number;
  y:          number;
  preference: string | null;
  is_blank:   boolean;
}

interface WinnerGroup {
  winner:  string;
  methods: string[];
  pct:     number;
}

interface PipelineStep {
  id:           string;
  label:        { fr: string; en: string };
  desc:         { fr: string; en: string };
  voters:       VoterSnap[];
  metrics:      Record<string, number | string | null>;
  winner_groups?: WinnerGroup[];
}

interface PipelineResult {
  steps:      PipelineStep[];
  candidates: { name: string; x: number; y: number; party: string }[];
  num_steps:  number;
}

// ── SVG voter scatter ─────────────────────────────────────────────────────────

const VoterScatter: React.FC<{
  step:       PipelineStep;
  candidates: PipelineResult['candidates'];
  candNames:  string[];
  animating:  boolean;
}> = ({ step, candidates, candNames, animating }) => {
  const colorMap: Record<string, string> = {};
  candNames.forEach((n, i) => { colorMap[n] = CAND_COLORS[i % CAND_COLORS.length]; });

  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      width="100%"
      style={{ display: 'block', maxHeight: 380 }}
    >
      {/* Grid */}
      {[-0.5, 0, 0.5].map((v) => (
        <React.Fragment key={v}>
          <line
            x1={domainToSvg(v, 'x')} y1={MARGIN}
            x2={domainToSvg(v, 'x')} y2={SVG_H - MARGIN}
            stroke={v === 0 ? '#adb5bd' : '#dee2e6'}
            strokeWidth={v === 0 ? 1 : 0.5}
            strokeDasharray={v === 0 ? undefined : '3 3'}
          />
          <line
            x1={MARGIN} y1={domainToSvg(v, 'y')}
            x2={SVG_W - MARGIN} y2={domainToSvg(v, 'y')}
            stroke={v === 0 ? '#adb5bd' : '#dee2e6'}
            strokeWidth={v === 0 ? 1 : 0.5}
            strokeDasharray={v === 0 ? undefined : '3 3'}
          />
        </React.Fragment>
      ))}

      {/* Voter dots */}
      {step.voters.map((v) => {
        const cx    = domainToSvg(v.x, 'x');
        const cy    = domainToSvg(v.y, 'y');
        const fill  = v.is_blank ? BLANK_COLOR : (v.preference ? (colorMap[v.preference] ?? '#888') : '#dee2e6');
        const op    = v.is_blank ? 0.35 : 0.55;
        const r     = v.is_blank ? 2 : 3;
        return (
          <circle
            key={v.id}
            cx={cx}
            cy={cy}
            r={r}
            fill={fill}
            fillOpacity={op}
            style={{ transition: animating ? 'fill 0.6s ease, fill-opacity 0.6s ease, r 0.3s ease' : 'none' }}
          />
        );
      })}

      {/* Candidate stars */}
      {candidates.map((c, idx) => {
        const cx    = domainToSvg(c.x, 'x');
        const cy    = domainToSvg(c.y, 'y');
        const color = PARTY_COLORS[c.party] ?? CAND_COLORS[idx % CAND_COLORS.length];
        return (
          <g key={c.name} transform={`translate(${cx},${cy})`}>
            <text
              textAnchor="middle" dominantBaseline="central"
              fontSize={20} fill={color} stroke="#fff" strokeWidth={0.8}
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >★</text>
            <text
              y={-18} textAnchor="middle" fontSize={10}
              fill={color} fontWeight={600}
              stroke="#fff" strokeWidth={2.5} paintOrder="stroke"
              style={{ pointerEvents: 'none' }}
            >{c.name}</text>
          </g>
        );
      })}
    </svg>
  );
};

// ── Stepper ───────────────────────────────────────────────────────────────────

const Stepper: React.FC<{
  steps:   PipelineStep[];
  current: number;
  onSelect: (i: number) => void;
  lang:    'fr' | 'en';
}> = ({ steps, current, onSelect, lang }) => (
  <div className="d-flex align-items-center gap-1 flex-wrap mb-3">
    {steps.map((s, i) => (
      <React.Fragment key={s.id}>
        <button
          type="button"
          onClick={() => onSelect(i)}
          className="d-flex flex-column align-items-center border-0 rounded-3 px-2 py-1"
          style={{
            background: i === current ? 'var(--bs-primary)' : 'var(--bs-secondary-bg, #f8f9fa)',
            color:      i === current ? '#fff' : 'var(--bs-body-color)',
            cursor:     'pointer',
            transition: 'all 0.2s',
            minWidth:   70,
            fontSize:   '0.72rem',
          }}
          data-testid={`pipeline-step-${s.id}`}
        >
          <span style={{ fontSize: '1.1rem' }}>{STEP_ICONS[s.id] ?? '●'}</span>
          <span className="fw-semibold" style={{ lineHeight: 1.2 }}>
            {s.label[lang]}
          </span>
        </button>
        {i < steps.length - 1 && (
          <span style={{ color: 'var(--bs-border-color)', fontSize: '1.2rem', lineHeight: 1 }}>→</span>
        )}
      </React.Fragment>
    ))}
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

const ElectionPipelineAnimator: React.FC = () => {
  const { t }           = useTranslation();
  const lang            = (i18n.language?.startsWith('en') ? 'en' : 'fr') as 'fr' | 'en';
  const { config }      = useElection();

  const [pipeline,     setPipeline]     = useState<PipelineResult | null>(null);
  const [currentStep,  setCurrentStep]  = useState(0);
  const [playing,      setPlaying]      = useState(false);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [animating,    setAnimating]    = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const runIdRef    = useRef(0);

  // ── Fetch pipeline ────────────────────────────────────────────────────
  const fetchPipeline = useCallback(async () => {
    const myRun = ++runIdRef.current;
    setLoading(true);
    setError(null);
    setPipeline(null);
    setCurrentStep(0);
    setPlaying(false);
    try {
      const res = await axios.post<PipelineResult>(`${API_BASE}${apiPath('election/simulate-pipeline')}`, {
        ...config,
        num_voters: Math.min(config.num_voters, 150),
      });
      if (runIdRef.current === myRun) {
        setPipeline(res.data);
        setCurrentStep(0);
      }
    } catch {
      if (runIdRef.current === myRun) setError(t('pipeline.error'));
    } finally {
      if (runIdRef.current === myRun) setLoading(false);
    }
  }, [config, t]);

  // ── Auto-play ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!playing || !pipeline) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      setCurrentStep((s) => {
        if (s >= pipeline.steps.length - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 1800);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [playing, pipeline]);

  // ── Trigger animation flag on step change ─────────────────────────────
  useEffect(() => {
    setAnimating(true);
    const id = setTimeout(() => setAnimating(false), 700);
    return () => clearTimeout(id);
  }, [currentStep]);

  const step       = pipeline?.steps[currentStep];
  const candNames  = pipeline?.candidates.map((c) => c.name) ?? [];
  const totalSteps = pipeline?.steps.length ?? 0;

  return (
    <div>
      {/* Controls */}
      <div className="d-flex align-items-center gap-2 mb-3 flex-wrap">
        <Button
          variant="primary" size="sm"
          onClick={fetchPipeline}
          disabled={loading}
        >
          {loading
            ? <><Spinner size="sm" className="me-2" />{t('pipeline.loading')}</>
            : t('pipeline.run')}
        </Button>
        {pipeline && (
          <>
            <Button
              variant={playing ? 'warning' : 'outline-primary'}
              size="sm"
              onClick={() => setPlaying((p) => !p)}
              disabled={currentStep >= totalSteps - 1 && !playing}
            >
              {playing ? '⏸ Pause' : '▶ Jouer'}
            </Button>
            <Button
              variant="outline-secondary" size="sm"
              onClick={() => setCurrentStep((s) => Math.min(s + 1, totalSteps - 1))}
              disabled={currentStep >= totalSteps - 1 || playing}
            >
              → {t('pipeline.next')}
            </Button>
            <Button
              variant="outline-secondary" size="sm"
              onClick={() => { setCurrentStep(0); setPlaying(false); }}
            >
              ↺ {t('pipeline.restart')}
            </Button>
            <span className="text-muted small">
              {t('pipeline.stepOf', { current: currentStep + 1, total: totalSteps })}
            </span>
          </>
        )}
      </div>

      {error && <Alert variant="danger" className="py-2">{error}</Alert>}

      {!pipeline && !loading && (
        <Alert variant="info" className="py-2">{t('pipeline.prompt')}</Alert>
      )}

      {pipeline && step && (
        <Row className="g-3">
          {/* Stepper */}
          <Col xs={12}>
            <Stepper
              steps={pipeline.steps}
              current={currentStep}
              onSelect={(i) => { setCurrentStep(i); setPlaying(false); }}
              lang={lang}
            />
          </Col>

          {/* SVG scatter */}
          <Col xs={12} md={7}>
            <Card>
              <Card.Header className="py-2 d-flex align-items-center gap-2">
                <span style={{ fontSize: '1.2rem' }}>{STEP_ICONS[step.id]}</span>
                <div>
                  <strong style={{ fontSize: '0.88rem' }}>{step.label[lang]}</strong>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>{step.desc[lang]}</div>
                </div>
              </Card.Header>
              <Card.Body className="p-2">
                <VoterScatter
                  step={step}
                  candidates={pipeline.candidates}
                  candNames={candNames}
                  animating={animating}
                />
                {/* Colour legend */}
                <div className="d-flex gap-3 mt-1 flex-wrap" style={{ fontSize: '0.72rem' }}>
                  {candNames.map((name, idx) => (
                    <span key={name} className="d-flex align-items-center gap-1">
                      <span style={{ width: 9, height: 9, borderRadius: 2, background: CAND_COLORS[idx % CAND_COLORS.length], display: 'inline-block' }} />
                      {name}
                    </span>
                  ))}
                  {pipeline.steps.some((s) => s.voters.some((v) => v.is_blank)) && (
                    <span className="d-flex align-items-center gap-1">
                      <span style={{ width: 9, height: 9, borderRadius: 2, background: BLANK_COLOR, display: 'inline-block', opacity: 0.5 }} />
                      Vote blanc
                    </span>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>

          {/* Step-specific info panel */}
          <Col xs={12} md={5}>
            <Card className="h-100">
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('pipeline.metricsTitle')}</strong>
              </Card.Header>
              <Card.Body className="p-3">

                {/* Generic metrics */}
                {step.metrics.num_voters && (
                  <MetricRow icon="👥" label={t('pipeline.metricVoters')} value={String(step.metrics.num_voters)} />
                )}
                {step.metrics.changed !== undefined && (
                  <MetricRow
                    icon="🔄"
                    label={t('pipeline.metricChanged')}
                    value={String(step.metrics.changed)}
                    variant={Number(step.metrics.changed) > 0 ? 'warning' : 'success'}
                  />
                )}
                {step.metrics.blank_rate !== undefined && (
                  <MetricRow
                    icon="□"
                    label={t('pipeline.metricBlankRate')}
                    value={`${Math.round(Number(step.metrics.blank_rate) * 100)}%`}
                    variant={Number(step.metrics.blank_rate) > 0.15 ? 'danger' : 'secondary'}
                  />
                )}
                {step.metrics.inter_method_agreement !== undefined && (
                  <MetricRow
                    icon="🤝"
                    label={t('pipeline.metricAgreement')}
                    value={`${Math.round(Number(step.metrics.inter_method_agreement) * 100)}%`}
                    variant={Number(step.metrics.inter_method_agreement) > 0.8 ? 'success' : 'warning'}
                  />
                )}
                {step.metrics.condorcet_winner !== undefined && (
                  <MetricRow
                    icon={step.metrics.condorcet_winner ? '✓' : '✗'}
                    label="Condorcet"
                    value={step.metrics.condorcet_winner ? String(step.metrics.condorcet_winner) : '—'}
                    variant={step.metrics.condorcet_winner ? 'success' : 'secondary'}
                  />
                )}

                {/* Donut for results step */}
                {step.id === 'results' && step.winner_groups && step.winner_groups.length > 0 && (
                  <div className="mt-3">
                    <MethodGroupDonut
                      methodGroups={step.winner_groups.map((g) => ({
                        winner:  g.winner,
                        methods: g.methods,
                        pct:     g.pct,
                      }))}
                      totalMethods={step.winner_groups.reduce((s, g) => s + g.methods.length, 0)}
                    />
                  </div>
                )}

                {/* Step navigation hint */}
                <div className="mt-auto pt-3" style={{ fontSize: '0.72rem', color: 'var(--bs-secondary-color)' }}>
                  {currentStep < totalSteps - 1
                    ? t('pipeline.nextStepHint', { next: pipeline.steps[currentStep + 1]?.label[lang] ?? '' })
                    : t('pipeline.finalStepHint')}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

// ── Metric row helper ─────────────────────────────────────────────────────────

const MetricRow: React.FC<{
  icon:     string;
  label:    string;
  value:    string;
  variant?: string;
}> = ({ icon, label, value, variant = 'secondary' }) => (
  <div className="d-flex align-items-center justify-content-between mb-2">
    <span style={{ fontSize: '0.8rem' }}>
      <span className="me-1">{icon}</span>
      {label}
    </span>
    <Badge bg={variant} style={{ fontSize: '0.72rem' }}>{value}</Badge>
  </div>
);

export default ElectionPipelineAnimator;
