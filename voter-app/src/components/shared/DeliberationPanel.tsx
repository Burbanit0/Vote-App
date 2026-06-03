/**
 * DeliberationPanel — simulates DeGroot deliberation before voting.
 * Compares pre-deliberation vs. post-deliberation election outcomes.
 * Shows how network structure (echo chamber vs. bridge) determines
 * whether deliberation polarises or converges the electorate.
 */
import React, { useCallback, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ElectResult {
  winner:           string | null;
  vote_shares:      Record<string, number>;
  condorcet_winner: string | null;
  mean_regret:      number;
  ideology_variance: number;
}

interface DelibData {
  pre_deliberation:  ElectResult;
  post_deliberation: ElectResult;
  winner_changed:    boolean;
  deliberation_effect: {
    opinion_shift_mean: number;
    convergence_rate:   number;
    polarization_change: number;
    regret_improvement: number;
  };
  per_round: { round: number; variance: number; mean_position: number; winner_if_voted_now: string | null }[];
  network_effect:   string;
  pedagogical_note: string;
}

// ── Network options ───────────────────────────────────────────────────────────

const NETWORK_OPTIONS = [
  { value: 'complete',     icon: '🌐', labelKey: 'delib.networkComplete' },
  { value: 'bridge',      icon: '🌉', labelKey: 'delib.networkBridge' },
  { value: 'random',      icon: '🎲', labelKey: 'delib.networkRandom' },
  { value: 'echo_chamber', icon: '📣', labelKey: 'delib.networkEcho' },
] as const;

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Main panel ────────────────────────────────────────────────────────────────

const DeliberationPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();
  const candidateNames = config.candidates.map((c) => c.name);

  const [network,      setNetwork]      = useState('random');
  const [rounds,       setRounds]       = useState(5);
  const [influence,    setInfluence]    = useState(0.3);
  const [groupSize,    setGroupSize]    = useState(5);
  const [argQuality,   setArgQuality]   = useState(0.5);
  const sim = $api.useMutation('post', '/api/v2/election/deliberation');
  const data: DelibData | null = (sim.data as DelibData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('delib.error') : null;

  const runSimulation = useCallback(() => {
    sim.mutate({ body: {
      candidates:          config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
      num_voters:          config.num_voters,
      ideology:            config.ideology,
      seed:                config.seed,
      deliberation_rounds: rounds,
      influence_weight:    influence,
      network_type:        network,
      group_size:          groupSize,
      argument_quality:    argQuality,
      method:              'plurality',
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, rounds, influence, network, groupSize, argQuality, t, sim]);

  // Chart data: per_round evolution
  const chartData = data
    ? [
        { round: 0, variance: data.pre_deliberation.ideology_variance, regret: data.pre_deliberation.mean_regret },
        ...(data.per_round.map((r) => ({ round: r.round, variance: r.variance, regret: 0 }))),
        { round: data.per_round.length + 1, variance: data.post_deliberation.ideology_variance, regret: data.post_deliberation.mean_regret },
      ]
    : [];

  const effect = data?.deliberation_effect;

  return (
    <div>
      {/* Network selector */}
      <Row className="g-2 mb-3">
        <Col xs={12}>
          <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>{t('delib.networkLabel')}</div>
          <div className="d-flex flex-wrap gap-2">
            {NETWORK_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                size="sm"
                variant={network === opt.value ? 'primary' : 'outline-secondary'}
                data-testid={`network-${opt.value}`}
                onClick={() => setNetwork(opt.value)}
              >
                {opt.icon} {t(opt.labelKey)}
              </Button>
            ))}
          </div>
        </Col>
      </Row>

      {/* Parameter sliders */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('delib.rounds')}: <strong>{rounds}</strong>
          </label>
          <Range min={1} max={10} step={1} value={rounds}
            data-testid="rounds-slider"
            onChange={(e) => setRounds(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('delib.influence')}: <strong>{influence.toFixed(2)}</strong>
          </label>
          <Range min={0} max={1} step={0.05} value={influence}
            data-testid="influence-slider"
            onChange={(e) => setInfluence(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('delib.argQuality')}: <strong>{argQuality.toFixed(2)}</strong>
          </label>
          <Range min={0} max={1} step={0.05} value={argQuality}
            data-testid="arg-quality-slider"
            onChange={(e) => setArgQuality(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading} data-testid="simulate-btn">
            {loading ? <Spinner size="sm" /> : t('delib.run')}
          </Button>
        </Col>
        {data && (
          <Col xs="auto">
            <PinToCentralButton
              type="deliberation"
              icon="🗣"
              label={t('delib.run')}
              summary={
                data.winner_changed
                  ? `${data.pre_deliberation.winner} → ${data.post_deliberation.winner}`
                  : `${data.post_deliberation.winner ?? '—'}`
              }
              methodsChanged={data.winner_changed ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('delib.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Winner comparison */}
          <div
            className={`d-flex align-items-center justify-content-around p-3 rounded mb-3 ${
              data.winner_changed ? 'border border-danger' : 'border border-success'
            }`}
            data-testid="comparison-banner"
          >
            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('delib.preVote')}</div>
              <Badge style={{ background: candColor(data.pre_deliberation.winner ?? '', candidateNames), fontSize: '0.85rem', padding: '6px 12px' }}
                data-testid="pre-winner-badge">
                {data.pre_deliberation.winner}
              </Badge>
            </div>
            <span style={{ fontSize: '1.4rem', color: data.winner_changed ? '#dc3545' : '#198754' }}>
              {data.winner_changed ? '⇒' : '='}
            </span>
            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('delib.postVote')}</div>
              <Badge style={{ background: candColor(data.post_deliberation.winner ?? '', candidateNames), fontSize: '0.85rem', padding: '6px 12px' }}
                data-testid="post-winner-badge">
                {data.post_deliberation.winner}
              </Badge>
            </div>
          </div>

          {data.winner_changed && (
            <Alert variant="danger" data-testid="winner-changed-alert">
              {t('delib.winnerChanged')}
            </Alert>
          )}

          {/* Effect badges */}
          {effect && (
            <div className="d-flex flex-wrap gap-2 mb-3" data-testid="effect-badges">
              <Badge
                variant={effect.polarization_change > 0 ? 'danger' : 'success'}
                data-testid="polarization-badge"
              >
                {t('delib.polarization')}: {effect.polarization_change >= 0 ? '+' : ''}{(effect.polarization_change * 100).toFixed(1)}%
              </Badge>
              <Badge
                variant={effect.regret_improvement > 0 ? 'success' : 'danger'}
                data-testid="regret-badge"
              >
                {t('delib.regret')}: {effect.regret_improvement >= 0 ? '' : ''}{effect.regret_improvement.toFixed(1)}%
              </Badge>
              <Badge variant="info" data-testid="convergence-badge">
                {t('delib.convergence')}: {(effect.convergence_rate * 100).toFixed(0)}%
              </Badge>
              <Badge variant="secondary" data-testid="shift-badge">
                {t('delib.shift')}: {effect.opinion_shift_mean.toFixed(3)}
              </Badge>
            </div>
          )}

          {/* Evolution chart */}
          <div data-testid="evolution-chart" className="mb-4">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>{t('delib.chartTitle')}</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="round" label={{ value: t('delib.roundLabel'), position: 'insideBottom', offset: -2, fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Line type="monotone" dataKey="variance" name={t('delib.variance')}
                  stroke="#dc3545" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Network effect note */}
          {data.network_effect && (
            <Alert variant="info" style={{ fontSize: '0.8rem' }} data-testid="network-effect-alert">
              <strong>🌐 {t('delib.networkEffect')}</strong> {data.network_effect}
            </Alert>
          )}

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('delib.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default DeliberationPanel;
