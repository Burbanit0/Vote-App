/**
 * EpistocracyPanel — Caplan (2007) rational irrationality & Brennan (2016) Against Democracy.
 * Simulates how voter competence distribution affects collective decision quality.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check, Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import PinToCentralButton from './PinToCentralButton';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SchemeResult {
  winner: string;
  bayesian_regret: number;
  correct_choice_pct: number;
  participates_pct: number;
}

interface EpistoData {
  voter_competence_stats: {
    mean: number;
    biased_mean: number;
    expert_count: number;
  };
  results: Record<string, SchemeResult>;
  democracy_vs_expert: {
    democracy_regret: number;
    expert_regret: number;
    omniscient_regret: number;
  };
  condorcet_threshold: number;
  pedagogical_note: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const SCHEMES = ['equal', 'competence_weighted', 'epistocratic', 'lottery'] as const;
type Scheme = (typeof SCHEMES)[number];

const SCHEME_COLORS: Record<Scheme, string> = {
  equal: '#dc3545',
  competence_weighted: '#fd7e14',
  epistocratic: '#0d6efd',
  lottery: '#6f42c1',
};

// ── Competence histogram SVG ──────────────────────────────────────────────────

interface HistogramProps {
  mean: number;
  std: number;
  expertPct: number;
  threshold: number;
  dist: string;
}

const CompetenceHistogram: React.FC<HistogramProps> = ({
  mean,
  std,
  expertPct,
  threshold,
  dist,
}) => {
  const W = 320,
    H = 130,
    padL = 30,
    padB = 20,
    padR = 10,
    padT = 10;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const bins = 20;

  // Approximate distribution shape for display
  const barData = Array.from({ length: bins }, (_, i) => {
    const x = (i + 0.5) / bins; // 0→1
    let density = 0;
    if (dist === 'bimodal') {
      const g1 = Math.exp(-((x - (mean - 0.15)) ** 2) / (2 * std ** 2)) * 0.6;
      const g2 = Math.exp(-((x - (mean + 0.2)) ** 2) / (2 * (std * 0.7) ** 2)) * 0.4;
      density = g1 + g2;
    } else if (dist === 'expert_minority') {
      const gLow = Math.exp(-((x - (mean - 0.05)) ** 2) / (2 * std ** 2)) * (1 - expertPct);
      const gHigh = Math.exp(-((x - 0.88) ** 2) / (2 * 0.05 ** 2)) * expertPct * 3;
      density = gLow + gHigh;
    } else {
      density = Math.exp(-((x - mean) ** 2) / (2 * std ** 2));
    }
    return density;
  });

  const maxD = Math.max(...barData, 0.001);
  const barW = chartW / bins;

  return (
    <svg
      data-testid="competence-histogram"
      width={W}
      height={H}
      style={{ display: 'block', fontFamily: 'monospace' }}
    >
      {/* Bars */}
      {barData.map((d, i) => {
        const bh = (d / maxD) * chartH;
        const bx = padL + i * barW;
        const by = padT + chartH - bh;
        const xMid = (i + 0.5) / bins;
        const color = xMid >= threshold ? '#0d6efd' : xMid >= 0.5 ? '#198754' : '#dc3545';
        return (
          <rect key={i} x={bx} y={by} width={barW - 1} height={bh} fill={color} opacity={0.7} />
        );
      })}
      {/* P=0.5 reference line */}
      <line
        x1={padL + chartW * 0.5}
        y1={padT}
        x2={padL + chartW * 0.5}
        y2={padT + chartH}
        stroke="#dc3545"
        strokeWidth={2}
        strokeDasharray="4 3"
      />
      <text x={padL + chartW * 0.5 + 2} y={padT + 10} style={{ fontSize: 9, fill: '#dc3545' }}>
        P=0.5
      </text>
      {/* Mean line */}
      <line
        x1={padL + chartW * mean}
        y1={padT}
        x2={padL + chartW * mean}
        y2={padT + chartH}
        stroke="#333"
        strokeWidth={1.5}
      />
      {/* Threshold line */}
      <line
        x1={padL + chartW * threshold}
        y1={padT}
        x2={padL + chartW * threshold}
        y2={padT + chartH}
        stroke="#0d6efd"
        strokeWidth={1}
        strokeDasharray="3 2"
      />
      {/* Axis */}
      <line x1={padL} y1={padT + chartH} x2={padL + chartW} y2={padT + chartH} stroke="#adb5bd" />
      <text x={padL} y={H - 4} style={{ fontSize: 9, fill: '#6c757d' }}>
        0
      </text>
      <text x={padL + chartW - 6} y={H - 4} style={{ fontSize: 9, fill: '#6c757d' }}>
        1
      </text>
      <text x={padL + chartW / 2 - 20} y={H - 4} style={{ fontSize: 9, fill: '#6c757d' }}>
        Compétence P
      </text>
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

export interface EpistocracyLabProps {
  labMode?: boolean;
  labCandidates?: Array<{ name: string; x: number; y: number }>;
  labNumVoters?: number;
  labSeed?: number;
}

const EpistocracyPanel: React.FC<EpistocracyLabProps> = ({
  labMode = false,
  labCandidates,
  labNumVoters,
  labSeed,
}) => {
  const { t } = useTranslation();

  const sim = $api.useMutation('post', '/api/v2/theory/epistocracy');
  const data: EpistoData | null = (sim.data as EpistoData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('episto.error') : null;

  const [numVoters, setNumVoters] = useState(200);
  const [seed, setSeed] = useState(42);
  const [compDist, setCompDist] = useState('uniform');
  const [compMean, setCompMean] = useState(0.55);
  const [compStd] = useState(0.15);
  const [expertPct, setExpertPct] = useState(0.1);
  const [caplanBias, setCaplanBias] = useState(true);
  const [threshold, setThreshold] = useState(0.7);
  const [activeView, setActiveView] = useState<'quality' | 'table'>('quality');

  const DEFAULT_CANDS = [
    { name: 'A', x: -0.5, y: 0.0 },
    { name: 'B', x: 0.0, y: 0.0 },
    { name: 'C', x: 0.5, y: 0.0 },
  ];

  const run = useCallback(
    (overrideCands?: typeof DEFAULT_CANDS, overrideVoters?: number, overrideSeed?: number) => {
      sim.mutate({
        body: {
          candidates: overrideCands ?? DEFAULT_CANDS,
          num_voters: overrideVoters ?? numVoters,
          seed: overrideSeed ?? seed,
          voter_competence_distribution: compDist,
          competence_params: {
            mean: compMean,
            std: compStd,
            expert_pct: expertPct,
            caplan_bias: caplanBias,
          },
          weighting_scheme: 'equal',
          epistocracy_threshold: threshold,
        },
      });
    },
    [numVoters, seed, compDist, compMean, compStd, expertPct, caplanBias, threshold, sim]
  );

  useEffect(() => {
    if (labMode && labCandidates?.length) {
      run(labCandidates, labNumVoters, labSeed);
    }
  }, [labMode, labCandidates, labNumVoters, labSeed]);

  // ── Chart data ─────────────────────────────────────────────────────────────
  const qualityChartData = data
    ? SCHEMES.map((s) => ({
        name: t(`episto.scheme_${s}`),
        quality: Math.round((data.results[s]?.correct_choice_pct ?? 0) * 100),
        regret: Math.round((data.results[s]?.bayesian_regret ?? 0) * 100),
        color: SCHEME_COLORS[s],
      }))
    : [];

  // Condorcet curve: P from 0.1 → 0.9 (approximate analytical)
  const condorcetCurve = Array.from({ length: 17 }, (_, i) => {
    const p = 0.1 + i * 0.05;
    // With N=200 voters, 3 candidates: accuracy ≈ sigmoid-like function of P
    // Simplified: P < 1/3 → below random; P > 1/3 → above
    const randChance = 1 / 3;
    const acc =
      p < 0.5
        ? Math.max(0, randChance - (0.5 - p) * 0.8)
        : Math.min(1, randChance + (p - 0.5) * 1.8);
    return { p: Math.round(p * 100), acc: Math.round(acc * 100) };
  });

  const stats = data?.voter_competence_stats;

  return (
    <div>
      {/* ── Caplan quote ── */}
      <Alert
        variant="warning"
        className="py-2 mb-3"
        data-testid="caplan-quote"
        style={{ fontSize: '0.78rem', borderLeft: '4px solid #ffc107' }}
      >
        <strong>{t('episto.caplanQuoteTitle')}</strong> {t('episto.caplanQuote')}
      </Alert>

      {/* ── Lab mode badge ── */}
      {labMode && (
        <div className="mb-2">
          <Badge variant="dark" style={{ fontSize: '0.68rem' }}>
            🔬 {t('lab.fromElectionLab')}
          </Badge>
        </div>
      )}
      {/* ── Controls: election config hidden in lab mode, episto params always shown ── */}
      <Row className="g-2 mb-2 items-end">
        {!labMode && (
          <>
            <Col xs={6} md={2}>
              <label className="mb-1 inline-block text-sm mb-0">{t('episto.voters')}</label>
              <Control
                type="number"
                size="sm"
                min={10}
                max={1000}
                value={numVoters}
                data-testid="voters-input"
                onChange={(e) => setNumVoters(Number(e.target.value))}
              />
            </Col>
            <Col xs={6} md={2}>
              <label className="mb-1 inline-block text-sm mb-0">{t('episto.seed')}</label>
              <Control
                type="number"
                size="sm"
                value={seed}
                data-testid="seed-input"
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </Col>
          </>
        )}
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">{t('episto.distribution')}</label>
          <Select
            size="sm"
            value={compDist}
            data-testid="dist-select"
            onChange={(e) => setCompDist(e.target.value)}
          >
            <option value="uniform">{t('episto.dist_uniform')}</option>
            <option value="bimodal">{t('episto.dist_bimodal')}</option>
            <option value="expert_minority">{t('episto.dist_expert_minority')}</option>
          </Select>
        </Col>
        <Col xs="auto">
          <Check
            type="switch"
            id="caplan-bias"
            checked={caplanBias}
            data-testid="caplan-bias-toggle"
            label={<span style={{ fontSize: '0.78rem' }}>{t('episto.caplanBias')}</span>}
            onChange={(e) => setCaplanBias(e.target.checked)}
          />
        </Col>
        <Col xs="auto">
          <Button
            variant="warning"
            size="sm"
            onClick={() =>
              run(
                labMode ? labCandidates : undefined,
                labMode ? labNumVoters : undefined,
                labMode ? labSeed : undefined
              )
            }
            disabled={loading}
            data-testid="run-btn"
          >
            {loading ? <Spinner size="sm" /> : t('episto.run')}
          </Button>
        </Col>
        {labMode && data && (
          <Col xs="auto">
            <PinToCentralButton
              type="epistocracy"
              icon="🎓"
              label={`${t('episto.cardTitle')} — P=${Math.round(data.voter_competence_stats.biased_mean * 100)}%`}
              summary={`${t('episto.democracyRegret')}: ${Math.round(data.democracy_vs_expert.democracy_regret * 100)}% / ${t('episto.expertRegret')}: ${Math.round(data.democracy_vs_expert.expert_regret * 100)}%`}
              methodsChanged={data.voter_competence_stats.biased_mean < 0.5 ? 2 : 0}
              disabled={!data}
            />
          </Col>
        )}
      </Row>

      {/* ── Competence sliders ── */}
      <Row className="g-2 mb-3 items-center">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('episto.compMean')} — {Math.round(compMean * 100)}%
          </label>
          <Range
            min={10}
            max={95}
            step={5}
            value={Math.round(compMean * 100)}
            data-testid="comp-mean-slider"
            onChange={(e) => setCompMean(Number(e.target.value) / 100)}
          />
        </Col>
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('episto.epThreshold')} — {Math.round(threshold * 100)}%
          </label>
          <Range
            min={50}
            max={95}
            step={5}
            value={Math.round(threshold * 100)}
            data-testid="threshold-slider"
            onChange={(e) => setThreshold(Number(e.target.value) / 100)}
          />
        </Col>
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('episto.expertPct')} — {Math.round(expertPct * 100)}%
          </label>
          <Range
            min={5}
            max={50}
            step={5}
            value={Math.round(expertPct * 100)}
            data-testid="expert-pct-slider"
            onChange={(e) => setExpertPct(Number(e.target.value) / 100)}
          />
        </Col>
      </Row>

      {/* ── Histogram ── */}
      <div className="mb-3" data-testid="histogram-section">
        <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
          {t('episto.histogramTitle')}
          {stats && (
            <span className="ms-2">
              <Badge variant="secondary" style={{ fontSize: '0.65rem' }}>
                μ={Math.round(stats.mean * 100)}%
              </Badge>
              {caplanBias && (
                <Badge variant="danger" className="ms-1" style={{ fontSize: '0.65rem' }}>
                  μ(biaisé)={Math.round(stats.biased_mean * 100)}%
                </Badge>
              )}
              <Badge variant="info" className="ms-1" style={{ fontSize: '0.65rem' }}>
                {stats.expert_count} experts
              </Badge>
            </span>
          )}
        </div>
        <CompetenceHistogram
          mean={compMean}
          std={compStd}
          expertPct={expertPct}
          threshold={threshold}
          dist={compDist}
        />
        <div className="flex gap-3 mt-1" style={{ fontSize: '0.65rem' }}>
          <span>
            <span style={{ color: '#dc3545' }}>■</span> P&lt;0.5 (nuisible)
          </span>
          <span>
            <span style={{ color: '#198754' }}>■</span> 0.5≤P&lt;seuil
          </span>
          <span>
            <span style={{ color: '#0d6efd' }}>■</span> P≥seuil (épistocracie)
          </span>
        </div>
      </div>

      {!data && !loading && !error && (
        <Alert variant="secondary" data-testid="prompt-alert">
          {t('episto.prompt')}
        </Alert>
      )}
      {error && (
        <Alert variant="danger" data-testid="error-alert">
          {error}
        </Alert>
      )}

      {data && (
        <>
          {/* ── Democracy below random warning ── */}
          {data.voter_competence_stats.biased_mean < 0.5 && (
            <Alert variant="danger" className="py-2" data-testid="below-random-alert">
              ⚠️{' '}
              {t('episto.belowRandom', {
                pct: Math.round(data.voter_competence_stats.biased_mean * 100),
              })}
            </Alert>
          )}

          {/* ── Democracy vs Expert badges ── */}
          <div className="flex flex-wrap gap-2 mb-3" data-testid="comparison-badges">
            <Badge variant="danger" style={{ fontSize: '0.72rem' }}>
              🗳 {t('episto.democracyRegret')}:{' '}
              {Math.round(data.democracy_vs_expert.democracy_regret * 100)}%
            </Badge>
            <Badge variant="info" style={{ fontSize: '0.72rem' }}>
              🎓 {t('episto.expertRegret')}:{' '}
              {Math.round(data.democracy_vs_expert.expert_regret * 100)}%
            </Badge>
            <Badge variant="success" style={{ fontSize: '0.72rem' }}>
              ✓ {t('episto.omniscient')}: 0%
            </Badge>
          </div>

          {/* ── View switcher ── */}
          <div className="flex gap-2 mb-3">
            {(['quality', 'table'] as const).map((v) => (
              <Button
                key={v}
                size="sm"
                variant={activeView === v ? 'dark' : 'outline-secondary'}
                data-testid={`view-btn-${v}`}
                onClick={() => setActiveView(v)}
              >
                {t(`episto.view_${v}`)}
              </Button>
            ))}
          </div>

          {/* ── Quality chart ── */}
          {activeView === 'quality' && (
            <div data-testid="quality-view">
              <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('episto.qualityTitle')}
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={qualityChartData}
                  margin={{ top: 5, right: 20, bottom: 20, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                  <ReferenceLine
                    y={33}
                    stroke="#adb5bd"
                    strokeDasharray="4 3"
                    label={{ value: t('episto.randomChance'), fontSize: 9, fill: '#6c757d' }}
                  />
                  <Bar dataKey="quality" name={t('episto.correctPct')} radius={[3, 3, 0, 0]}>
                    {qualityChartData.map((pt, i) => (
                      <Cell key={i} fill={pt.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              {/* Condorcet curve */}
              <div className="font-semibold mt-3 mb-1" style={{ fontSize: '0.82rem' }}>
                {t('episto.condorcetTitle')}
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart
                  data={condorcetCurve}
                  margin={{ top: 5, right: 20, bottom: 20, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="p"
                    unit="%"
                    tick={{ fontSize: 10 }}
                    label={{
                      value: 'P moyen',
                      position: 'insideBottom',
                      offset: -10,
                      fontSize: 10,
                    }}
                  />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                  <ReferenceLine
                    y={33}
                    stroke="#dc3545"
                    strokeDasharray="4 3"
                    label={{
                      value: t('episto.randomChance'),
                      fontSize: 9,
                      fill: '#dc3545',
                      position: 'right',
                    }}
                  />
                  <ReferenceLine
                    x={Math.round(compMean * 100)}
                    stroke="#333"
                    strokeWidth={2}
                    label={{
                      value: t('episto.currentP'),
                      fontSize: 9,
                      fill: '#333',
                      position: 'top',
                    }}
                  />
                  <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                  <Line
                    type="monotone"
                    dataKey="acc"
                    name={t('episto.collectiveAcc')}
                    stroke="#0d6efd"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Table view ── */}
          {activeView === 'table' && (
            <div data-testid="table-view">
              <table className="table table-sm table-bordered" style={{ fontSize: '0.74rem' }}>
                <thead className="table-light">
                  <tr>
                    <th>{t('episto.colScheme')}</th>
                    <th>{t('episto.colCorrect')}</th>
                    <th>{t('episto.colRegret')}</th>
                    <th>{t('episto.colParticipates')}</th>
                  </tr>
                </thead>
                <tbody>
                  {SCHEMES.map((s) => {
                    const r = data.results[s];
                    const isBest = SCHEMES.every(
                      (s2) => (data.results[s2]?.correct_choice_pct ?? 0) <= r.correct_choice_pct
                    );
                    return (
                      <tr
                        key={s}
                        style={{ background: isBest ? '#d1e7dd' : undefined }}
                        data-testid={`table-row-${s}`}
                      >
                        <td>
                          <Badge style={{ background: SCHEME_COLORS[s], fontSize: '0.65rem' }}>
                            {t(`episto.scheme_${s}`)}
                          </Badge>
                        </td>
                        <td
                          style={{
                            fontWeight: 700,
                            color: r.correct_choice_pct < 0.33 ? '#dc3545' : undefined,
                          }}
                        >
                          {Math.round(r.correct_choice_pct * 100)}%
                        </td>
                        <td>{Math.round(r.bayesian_regret * 100)}%</td>
                        <td>
                          {s === 'epistocratic' ? (
                            <span
                              style={{ color: r.participates_pct < 0.2 ? '#dc3545' : '#198754' }}
                            >
                              {Math.round(r.participates_pct * 100)}%
                            </span>
                          ) : (
                            '100%'
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Arguments for/against ── */}
          <Row className="g-2 mt-2" data-testid="arguments-section">
            <Col xs={12} md={6}>
              <div
                className="border border-border rounded p-2"
                style={{ background: '#fff3cd', fontSize: '0.74rem' }}
              >
                <div className="font-semibold mb-1">⚠ {t('episto.forTitle')}</div>
                <ul className="mb-0" style={{ paddingLeft: 14 }}>
                  <li>{t('episto.for1')}</li>
                  <li>{t('episto.for2')}</li>
                  <li>{t('episto.for3')}</li>
                </ul>
              </div>
            </Col>
            <Col xs={12} md={6}>
              <div
                className="border border-border rounded p-2"
                style={{ background: '#d1e7dd', fontSize: '0.74rem' }}
              >
                <div className="font-semibold mb-1">✓ {t('episto.againstTitle')}</div>
                <ul className="mb-0" style={{ paddingLeft: 14 }}>
                  <li>{t('episto.against1')}</li>
                  <li>{t('episto.against2')}</li>
                  <li>{t('episto.against3')}</li>
                </ul>
              </div>
            </Col>
          </Row>

          {/* ── Pedagogical note ── */}
          <Alert
            variant="secondary"
            className="mt-3"
            style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note"
          >
            <strong>{t('episto.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default EpistocracyPanel;
