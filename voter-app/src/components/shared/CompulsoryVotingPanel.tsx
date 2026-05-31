/**
 * CompulsoryVotingPanel — compares voluntary vs. compulsory voting
 * on the same electorate (Bradley effect of compulsion: reluctant voters
 * add null ballots and random votes, but improve representation).
 */
import React, { useCallback, useRef, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, ResponsiveContainer, Cell,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';

const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoterProfile { mean_ideology_x: number; partisan_pct: number; }
interface ElectResult {
  turnout:           number;
  winner:            string | null;
  vote_shares:       Record<string, number>;
  null_rate:         number;
  voter_profile?:    VoterProfile;
  reluctant_count?:  number;
  noise_effect?:     number;
  winners_by_method?: Record<string, string | null>;
}

interface CompulsoryData {
  voluntary:                    ElectResult;
  compulsory:                   ElectResult;
  winner_changed:               boolean;
  representation_improvement:   number;
  quality_degradation:          number;
  pedagogical_note:             string;
}

// ── Country examples sidebar ──────────────────────────────────────────────────

const EXAMPLES = [
  { flag: '🇦🇺', country: 'Australie',  system: 'Obligatoire (20 AUD amende)', turnout: '92%' },
  { flag: '🇧🇪', country: 'Belgique',   system: 'Obligatoire (symbolique)',    turnout: '88%' },
  { flag: '🇧🇷', country: 'Brésil',     system: 'Obligatoire (16-70 ans)',     turnout: '79%' },
  { flag: '🇫🇷', country: 'France',     system: 'Libre',                       turnout: '73% prés. / 48% légis.' },
  { flag: '🇺🇸', country: 'USA',        system: 'Libre',                       turnout: '55% prés. / 37% midterms' },
];

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22', '#e83e8c'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── 3-column result card ──────────────────────────────────────────────────────

interface ResultCardProps {
  title:          string;
  result:         ElectResult;
  candidateNames: string[];
  accent?:        string;
  testId:         string;
  t:              (k: string) => string;
}

const ResultCard: React.FC<ResultCardProps> = ({ title, result, candidateNames, accent, testId, t }) => {
  const barData = candidateNames.map((c) => ({
    name:  c,
    share: Math.round((result.vote_shares[c] ?? 0) * 100),
  }));

  return (
    <Card className="h-100" style={{ borderTop: accent ? `3px solid ${accent}` : undefined }}
      data-testid={testId}>
      <Card.Header className="py-1" style={{ fontSize: '0.8rem', fontWeight: 600 }}>
        {title}
      </Card.Header>
      <Card.Body className="py-2">
        <div className="d-flex gap-1 flex-wrap mb-2">
          <Badge bg="secondary" style={{ fontSize: '0.7rem' }}>
            {t('compulsory.turnout')}: {Math.round(result.turnout * 100)}%
          </Badge>
          <Badge bg="info" text="dark" style={{ fontSize: '0.7rem' }}>
            {t('compulsory.null')}: {Math.round(result.null_rate * 100)}%
          </Badge>
          {result.voter_profile && (
            <Badge bg="light" text="dark" style={{ fontSize: '0.7rem' }}>
              μ: {result.voter_profile.mean_ideology_x >= 0 ? '+' : ''}{result.voter_profile.mean_ideology_x.toFixed(2)}
            </Badge>
          )}
        </div>
        <div className="fw-semibold mb-1" style={{ fontSize: '0.78rem', color: accent }}>
          {t('compulsory.winner')}: {result.winner ?? '—'}
        </div>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={barData} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 9 }} />
            <YAxis unit="%" domain={[0, 60]} tick={{ fontSize: 9 }} />
            <Tooltip formatter={(v: number) => `${v}%`} />
            <Bar dataKey="share">
              {barData.map((entry, i) => (
                <Cell key={i} fill={candColor(entry.name, candidateNames)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const CompulsoryVotingPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();
  const candidateNames = config.candidates.map((c) => c.name);

  const [volTurnout,  setVolTurnout]  = useState(0.65);
  const [compTurnout, setCompTurnout] = useState(0.92);
  const [relNull,     setRelNull]     = useState(0.04);
  const [relRandom,   setRelRandom]   = useState(0.08);

  const sim = $api.useMutation('post', '/api/v2/election/compulsory-voting');
  const data: CompulsoryData | null = (sim.data as CompulsoryData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('compulsory.error') : null;

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback((vt: number, ct: number, rn: number, rr: number) => {
    sim.mutate({ body: {
      candidates:           config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
      num_voters:           config.num_voters,
      ideology:             config.ideology,
      seed:                 config.seed,
      voluntary_turnout:    vt,
      compulsory_turnout:   ct,
      reluctant_null_rate:  rn,
      reluctant_random_pct: rr,
      method:               'plurality',
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, sim]);

  const handleSimulate = () => runSimulation(volTurnout, compTurnout, relNull, relRandom);

  const schedule = useCallback((vt: number, ct: number, rn: number, rr: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(vt, ct, rn, rr), DEBOUNCE_MS);
  }, [runSimulation]);

  return (
    <div>
      <Row className="g-3">
        {/* Main content */}
        <Col xs={12} md={9}>
          {/* Controls */}
          <Row className="g-2 mb-3 align-items-end">
            <Col xs={6} md={3}>
              <Form.Label className="small mb-0">
                {t('compulsory.volTurnout')}: <strong>{Math.round(volTurnout * 100)}%</strong>
              </Form.Label>
              <Form.Range data-testid="vol-turnout-slider"
                min={0.4} max={0.9} step={0.05} value={volTurnout}
                onChange={(e) => { setVolTurnout(Number(e.target.value)); schedule(Number(e.target.value), compTurnout, relNull, relRandom); }}
              />
            </Col>
            <Col xs={6} md={3}>
              <Form.Label className="small mb-0">
                {t('compulsory.compTurnout')}: <strong>{Math.round(compTurnout * 100)}%</strong>
              </Form.Label>
              <Form.Range data-testid="comp-turnout-slider"
                min={0.7} max={0.99} step={0.05} value={compTurnout}
                onChange={(e) => { setCompTurnout(Number(e.target.value)); schedule(volTurnout, Number(e.target.value), relNull, relRandom); }}
              />
            </Col>
            <Col xs={6} md={3}>
              <Form.Label className="small mb-0">
                {t('compulsory.nullRate')}: <strong>{Math.round(relNull * 100)}%</strong>
              </Form.Label>
              <Form.Range data-testid="null-rate-slider"
                min={0} max={0.15} step={0.01} value={relNull}
                onChange={(e) => { setRelNull(Number(e.target.value)); schedule(volTurnout, compTurnout, Number(e.target.value), relRandom); }}
              />
            </Col>
            <Col xs={6} md={3}>
              <Form.Label className="small mb-0">
                {t('compulsory.randomPct')}: <strong>{Math.round(relRandom * 100)}%</strong>
              </Form.Label>
              <Form.Range data-testid="random-pct-slider"
                min={0} max={0.5} step={0.05} value={relRandom}
                onChange={(e) => { setRelRandom(Number(e.target.value)); schedule(volTurnout, compTurnout, relNull, Number(e.target.value)); }}
              />
            </Col>
          </Row>

          <div className="d-flex gap-2 mb-3 flex-wrap">
            <Button variant="primary" onClick={handleSimulate} disabled={loading}>
              {loading ? <Spinner size="sm" animation="border" /> : t('compulsory.run')}
            </Button>
            {data && (() => {
              const vbm = data.voluntary.winners_by_method ?? {};
              const cbm = data.compulsory.winners_by_method ?? {};
              let changedCount = 0;
              Object.entries(cbm).forEach(([m, w]) => {
                if (w !== vbm[m]) changedCount += 1;
              });
              if (changedCount === 0 && data.winner_changed) changedCount = 1;
              return (
                <PinToCentralButton
                  type="compulsory"
                  icon="⚖️"
                  label={`${t('compulsory.run')} — ${Math.round(compTurnout * 100)}%`}
                  summary={
                    changedCount > 0
                      ? `${changedCount}/${Object.keys(cbm).length || 1} ${t('lab.methodsChanged')}`
                      : `${t('compulsory.run')}: ${data.compulsory.winner ?? '—'}`
                  }
                  methodsChanged={changedCount}
                  winnersByMethod={data.compulsory.winners_by_method}
                />
              );
            })()}
          </div>

          {!data && !loading && !error && (
            <Alert variant="info" role="alert">{t('compulsory.prompt')}</Alert>
          )}
          {error && <Alert variant="danger">{error}</Alert>}

          {data && (
            <>
              {/* 3-column comparison */}
              <Row className="g-2 mb-3">
                <Col xs={6}>
                  <ResultCard title={t('compulsory.voluntary')} result={data.voluntary}
                    candidateNames={candidateNames} accent="#005CAB"
                    testId="voluntary-card" t={t} />
                </Col>
                <Col xs={6}>
                  <ResultCard title={t('compulsory.compulsoryLabel')} result={data.compulsory}
                    candidateNames={candidateNames} accent="#C8590A"
                    testId="compulsory-card" t={t} />
                </Col>
              </Row>

              {/* Winner changed */}
              {data.winner_changed && (
                <Alert variant="danger" data-testid="winner-changed-alert">
                  {t('compulsory.winnerChanged')}: {data.voluntary.winner} → {data.compulsory.winner}
                </Alert>
              )}

              {/* Two metrics in tension */}
              <Row className="g-2 mb-3" data-testid="metrics-row">
                <Col xs={12} md={6}>
                  <div className="border border-success rounded p-2 h-100">
                    <div className="fw-semibold" style={{ color: '#198754', fontSize: '0.82rem' }}>
                      📈 {t('compulsory.repImprovement')}
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#198754' }}>
                      {data.representation_improvement >= 0 ? '+' : ''}{data.representation_improvement.toFixed(3)}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#6c757d' }}>
                      {t('compulsory.repImprovementDesc')}
                    </div>
                    <Badge bg="success" data-testid="representation-badge" className="mt-1">
                      Δ {data.representation_improvement.toFixed(3)}
                    </Badge>
                  </div>
                </Col>
                <Col xs={12} md={6}>
                  <div className="border border-danger rounded p-2 h-100">
                    <div className="fw-semibold" style={{ color: '#dc3545', fontSize: '0.82rem' }}>
                      📉 {t('compulsory.qualityDegradation')}
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#dc3545' }}>
                      +{Math.round(data.quality_degradation * 100)}%
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#6c757d' }}>
                      {t('compulsory.qualityDegradationDesc')}
                    </div>
                    <Badge bg="danger" data-testid="quality-badge" className="mt-1">
                      +{Math.round(data.quality_degradation * 100)}% {t('compulsory.noise')}
                    </Badge>
                    {data.compulsory.reluctant_count != null && (
                      <Badge bg="warning" text="dark" data-testid="reluctant-badge" className="ms-1 mt-1">
                        {data.compulsory.reluctant_count} {t('compulsory.reluctant')}
                      </Badge>
                    )}
                  </div>
                </Col>
              </Row>

              {/* Pedagogical note */}
              <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
                <strong>{t('compulsory.noteTitle')}</strong> {data.pedagogical_note}
              </Alert>
            </>
          )}
        </Col>

        {/* Sidebar: country examples */}
        <Col xs={12} md={3}>
          <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>
            {t('compulsory.examplesTitle')}
          </div>
          <div data-testid="examples-sidebar">
            {EXAMPLES.map((ex) => (
              <div key={ex.country} className="border rounded p-2 mb-2"
                style={{ fontSize: '0.72rem', background: '#f8f9fa' }}>
                <div><strong>{ex.flag} {ex.country}</strong></div>
                <div className="text-muted">{ex.system}</div>
                <Badge bg="primary" style={{ fontSize: '0.65rem' }}>{ex.turnout}</Badge>
              </div>
            ))}
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default CompulsoryVotingPanel;
