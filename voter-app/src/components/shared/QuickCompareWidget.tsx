import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useElection } from '../../stores/useElectionStore';
import { simulateElection } from '../../services/electionApi';

// ── Scenario definitions (widget-local, minimal configs) ──────────────────────

const WIDGET_SCENARIOS = {
  france2002: {
    flag: '🇫🇷',
    labelKey: 'home.widget.scenarioFrance2002',
    phenKey: 'home.widget.phenParadox',
    config: {
      candidates: [
        { name: 'Chirac', x: 0.3, y: 0.4 },
        { name: 'Jospin', x: -0.4, y: -0.3 },
        { name: 'Le Pen', x: 0.8, y: 0.8 },
        { name: 'Bayrou', x: 0.1, y: 0.1 },
        { name: 'Taubira', x: -0.7, y: -0.6 },
        { name: 'Besancenot', x: -0.8, y: -0.5 },
      ],
      num_voters: 200,
      ideology: 'polarized',
      seed: 2002,
      blank_vote: {
        enabled: false,
        rule: 'symbolic' as const,
        contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' as const },
      },
      information_model: {
        enabled: false,
        media_bias: {},
        voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
      },
      campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
    },
  },
  usa1992: {
    flag: '🇺🇸',
    labelKey: 'home.widget.scenarioUSA1992',
    phenKey: 'home.widget.phenSpoiler',
    config: {
      candidates: [
        { name: 'Clinton', x: -0.2, y: -0.1 },
        { name: 'Bush', x: 0.4, y: 0.5 },
        { name: 'Perot', x: 0.1, y: 0.0 },
      ],
      num_voters: 200,
      ideology: 'random',
      seed: 1992,
      blank_vote: {
        enabled: false,
        rule: 'symbolic' as const,
        contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' as const },
      },
      information_model: {
        enabled: false,
        media_bias: {},
        voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
      },
      campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
    },
  },
  consensus: {
    flag: '✅',
    labelKey: 'home.widget.scenarioConsensus',
    phenKey: 'home.widget.phenConsensus',
    config: {
      candidates: [
        { name: 'Centre', x: 0.0, y: 0.0 },
        { name: 'Gauche Mod.', x: -0.3, y: -0.2 },
        { name: 'Droite Mod.', x: 0.3, y: 0.2 },
      ],
      num_voters: 200,
      ideology: 'centrist',
      seed: 77,
      blank_vote: {
        enabled: false,
        rule: 'symbolic' as const,
        contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' as const },
      },
      information_model: {
        enabled: false,
        media_bias: {},
        voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
      },
      campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
    },
  },
  condorcet_cycle: {
    flag: '🌀',
    labelKey: 'home.widget.scenarioCycle',
    phenKey: 'home.widget.phenCycle',
    config: {
      candidates: [
        { name: 'Alice', x: -0.5, y: 0.3 },
        { name: 'Bob', x: 0.4, y: -0.2 },
        { name: 'Carol', x: 0.0, y: -0.5 },
      ],
      num_voters: 200,
      ideology: 'polarized',
      seed: 314,
      blank_vote: {
        enabled: false,
        rule: 'symbolic' as const,
        contagion: { enabled: false, beta: 0.1, gamma: 0.1, network: 'random' as const },
      },
      information_model: {
        enabled: false,
        media_bias: {},
        voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 },
      },
      campaign: { enabled: false, num_days: 30, polling_effect: 0.3 },
    },
  },
} as const;

type ScenarioId = keyof typeof WIDGET_SCENARIOS;

const METHODS = [
  'plurality',
  'two_round',
  'borda',
  'approval',
  'irv',
  'schulze',
  'star_voting',
  'median_voting',
];

// ── Component ─────────────────────────────────────────────────────────────────

const QuickCompareWidget: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { applyScenario } = useElection();

  const [selected, setSelected] = useState<ScenarioId>('france2002');
  const [methodA, setMethodA] = useState('plurality');
  const [methodB, setMethodB] = useState('schulze');
  const [winnerA, setWinnerA] = useState<string | null>(null);
  const [winnerB, setWinnerB] = useState<string | null>(null);
  const [regretA, setRegretA] = useState<number | null>(null);
  const [regretB, setRegretB] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasResult, setHasResult] = useState(false);

  const runIdRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSim = useCallback(async (scenarioId: ScenarioId, mA: string, mB: string) => {
    const myRun = ++runIdRef.current;
    setLoading(true);
    try {
      const config = WIDGET_SCENARIOS[scenarioId].config;
      const res = await simulateElection(config as any);
      if (runIdRef.current !== myRun) return;
      setWinnerA(res.methods[mA]?.winner ?? '—');
      setWinnerB(res.methods[mB]?.winner ?? '—');
      setRegretA(res.methods[mA]?.bayesian_regret ?? null);
      setRegretB(res.methods[mB]?.bayesian_regret ?? null);
      setHasResult(true);
    } catch {
      if (runIdRef.current === myRun) {
        setWinnerA(null);
        setWinnerB(null);
      }
    } finally {
      if (runIdRef.current === myRun) setLoading(false);
    }
  }, []);

  // Debounce 400ms on any param change
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => runSim(selected, methodA, methodB), 400);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [selected, methodA, methodB, runSim]);

  const handleExplore = () => {
    applyScenario(selected);
    navigate('/election-lab');
  };

  const differ = hasResult && winnerA && winnerB && winnerA !== winnerB;
  const agree = hasResult && winnerA && winnerB && winnerA === winnerB;

  return (
    <div className="rounded-4 p-4 p-md-5" style={{ background: 'var(--bs-secondary-bg, #f8f9fa)' }}>
      <h2 className="font-bold text-center mb-1" style={{ fontSize: '1.4rem' }}>
        {t('home.widget.title')}
      </h2>
      <p className="text-muted-foreground text-center mb-4" style={{ fontSize: '0.9rem' }}>
        {t('home.widget.subtitle')}
      </p>

      {/* Step 1 — Scenario selection */}
      <div className="mb-4">
        <div className="text-sm font-semibold text-muted-foreground mb-2">
          1. {t('home.widget.step1')}
        </div>
        <Row className="g-2">
          {(
            Object.entries(WIDGET_SCENARIOS) as [
              ScenarioId,
              (typeof WIDGET_SCENARIOS)[ScenarioId],
            ][]
          ).map(([id, sc]) => (
            <Col key={id} xs={6} md={3}>
              <button
                type="button"
                className="w-full rounded-3 border border-border p-2 text-left"
                style={{
                  cursor: 'pointer',
                  background:
                    selected === id ? 'var(--bs-primary-bg-subtle, #cfe2ff)' : 'var(--bs-body-bg)',
                  borderColor: selected === id ? 'var(--bs-primary)' : 'var(--bs-border-color)',
                  borderWidth: selected === id ? 2 : 1,
                  transition: 'all 0.15s',
                }}
                onClick={() => setSelected(id)}
                aria-pressed={selected === id}
              >
                <div style={{ fontSize: '1.4rem', lineHeight: 1 }}>{sc.flag}</div>
                <div className="font-semibold" style={{ fontSize: '0.8rem', marginTop: 4 }}>
                  {t(sc.labelKey)}
                </div>
                <div className="text-muted-foreground" style={{ fontSize: '0.7rem' }}>
                  {t(sc.phenKey)}
                </div>
              </button>
            </Col>
          ))}
        </Row>
      </div>

      {/* Step 2 — Method selection */}
      <div className="mb-4">
        <div className="text-sm font-semibold text-muted-foreground mb-2">
          2. {t('home.widget.step2')}
        </div>
        <Row className="g-2 items-center">
          <Col xs={12} sm={5}>
            <Select
              size="sm"
              value={methodA}
              onChange={(e) => setMethodA(e.target.value)}
              style={{ borderLeft: '3px solid #005CAB' }}
              aria-label={t('home.widget.methodA')}
            >
              {METHODS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={2} className="text-center text-muted-foreground text-sm">
            {t('home.widget.vs')}
          </Col>
          <Col xs={12} sm={5}>
            <Select
              size="sm"
              value={methodB}
              onChange={(e) => setMethodB(e.target.value)}
              style={{ borderLeft: '3px solid #C8590A' }}
              aria-label={t('home.widget.methodB')}
            >
              {METHODS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </Col>
        </Row>
        <p className="text-muted-foreground mb-0 mt-1" style={{ fontSize: '0.75rem' }}>
          {t('home.widget.helpText')}
        </p>
      </div>

      {/* Step 3 — Result */}
      <div>
        <div className="text-sm font-semibold text-muted-foreground mb-2">
          3. {t('home.widget.step3')}
        </div>

        {loading ? (
          <div className="text-center py-3 text-muted-foreground">
            <Spinner size="sm" className="me-2" />
            <span style={{ fontSize: '0.85rem' }}>{t('home.widget.loading')}</span>
          </div>
        ) : (
          <>
            <Row className="g-3 mb-3">
              <Col xs={6}>
                <div
                  className="rounded-3 p-3 text-center"
                  style={{ background: 'var(--bs-body-bg)', border: '2px solid #005CAB' }}
                >
                  <div className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                    {methodA}
                  </div>
                  <div className="font-bold mt-1" style={{ fontSize: '1.1rem', color: '#005CAB' }}>
                    {winnerA ?? '—'}
                  </div>
                  <div className="text-muted-foreground" style={{ fontSize: '0.7rem' }}>
                    {t('home.widget.elects')}
                  </div>
                </div>
              </Col>
              <Col xs={6}>
                <div
                  className="rounded-3 p-3 text-center"
                  style={{ background: 'var(--bs-body-bg)', border: '2px solid #C8590A' }}
                >
                  <div className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                    {methodB}
                  </div>
                  <div className="font-bold mt-1" style={{ fontSize: '1.1rem', color: '#C8590A' }}>
                    {winnerB ?? '—'}
                  </div>
                  <div className="text-muted-foreground" style={{ fontSize: '0.7rem' }}>
                    {t('home.widget.elects')}
                  </div>
                </div>
              </Col>
            </Row>

            {/* Divergence / consensus message */}
            {differ && (
              <div
                className="rounded-3 p-3 text-center mb-3"
                style={{
                  background: 'rgba(200,89,10,0.10)',
                  border: '1px solid rgba(200,89,10,0.3)',
                }}
              >
                <div className="font-semibold" style={{ fontSize: '0.9rem' }}>
                  {t('home.widget.diverge')}
                </div>
                <div className="text-muted-foreground" style={{ fontSize: '0.78rem' }}>
                  {t('home.widget.divergeHint')}
                </div>
              </div>
            )}
            {agree && (
              <div
                className="rounded-3 p-3 text-center mb-3"
                style={{
                  background: 'rgba(0,122,51,0.08)',
                  border: '1px solid rgba(0,122,51,0.25)',
                }}
              >
                <div className="font-semibold" style={{ fontSize: '0.9rem', color: '#007A33' }}>
                  {t('home.widget.agree')}
                </div>
              </div>
            )}

            {hasResult && (
              <div className="text-center">
                {/* Regret delta badge */}
                {regretA != null && regretB != null && (
                  <div className="mb-2">
                    <Badge
                      variant={regretA < regretB ? 'success' : 'secondary'}
                      data-testid="regret-delta-badge"
                      style={{ fontSize: '0.72rem' }}
                    >
                      Regret Δ: {Math.abs(regretA - regretB).toFixed(4)} (
                      {regretA < regretB ? methodA : methodB} {t('home.widget.lowerRegret')})
                    </Badge>
                  </div>
                )}
                <div className="flex gap-2 justify-center flex-wrap">
                  <Button variant="primary" onClick={handleExplore} data-testid="explore-button">
                    {t('home.widget.explore')}
                  </Button>
                  {differ && (
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => {
                        handleExplore();
                      }}
                      data-testid="full-duel-button"
                      style={{ fontSize: '0.8rem' }}
                    >
                      ⚔ {t('duel.openFull')} →
                    </Button>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default QuickCompareWidget;
