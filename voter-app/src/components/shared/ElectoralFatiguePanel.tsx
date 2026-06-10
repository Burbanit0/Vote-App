/**
 * ElectoralFatiguePanel — simulates how repeated elections reduce turnout
 * and progressively shift the residual electorate toward engaged (partisan) voters.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Control, Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface ElectionPoint {
  election_n: number;
  turnout: number;
  winner: string | null;
  voter_profile: {
    mean_ideology_x: number;
    partisan_pct: number;
  };
  vote_shares: Record<string, number>;
}

interface FatigueData {
  elections: ElectionPoint[];
  winner_drift: (string | null)[];
  winner_changed_at: number | null;
  ideology_drift: number;
  representation_gap: number;
  full_mean_ideology: number;
  pedagogical_note: string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22', '#e83e8c'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Who stops voting SVG ──────────────────────────────────────────────────────

const COMP_H = 80;

interface CompositionProps {
  elections: ElectionPoint[];
  t: (k: string) => string;
}

const VoterCompositionBars: React.FC<CompositionProps> = ({ elections, t }) => {
  if (!elections.length) return null;
  return (
    <div data-testid="composition-bars" className="mb-3">
      <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
        {t('fatigue.compositionTitle')}
      </div>
      <div className="flex gap-1 items-end">
        {elections.map((e) => {
          const partPct = Math.round(e.voter_profile.partisan_pct * 100);
          const casuals = 100 - partPct;
          return (
            <div
              key={e.election_n}
              className="flex flex-col items-center"
              style={{ flex: 1, minWidth: 24 }}
            >
              <div
                style={{
                  width: '100%',
                  height: COMP_H,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'flex-end',
                }}
              >
                <div
                  style={{
                    height: `${Math.round(e.turnout * COMP_H)}px`,
                    background: '#dee2e6',
                    borderRadius: '3px 3px 0 0',
                    overflow: 'hidden',
                  }}
                >
                  <div style={{ height: `${partPct}%`, background: '#dc3545', opacity: 0.85 }} />
                  <div style={{ height: `${casuals}%`, background: '#adb5bd', opacity: 0.6 }} />
                </div>
              </div>
              <div style={{ fontSize: '0.6rem', color: '#6c757d' }}>E{e.election_n}</div>
              <div style={{ fontSize: '0.6rem', color: '#6c757d' }}>
                {Math.round(e.turnout * 100)}%
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 mt-1" style={{ fontSize: '0.7rem', color: '#6c757d' }}>
        <span>
          <span
            style={{
              background: '#dc3545',
              display: 'inline-block',
              width: 10,
              height: 10,
              marginRight: 3,
              borderRadius: 2,
            }}
          />
          {t('fatigue.partisan')}
        </span>
        <span>
          <span
            style={{
              background: '#adb5bd',
              display: 'inline-block',
              width: 10,
              height: 10,
              marginRight: 3,
              borderRadius: 2,
            }}
          />
          {t('fatigue.casual')}
        </span>
      </div>
    </div>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const ElectoralFatiguePanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const candidateNames = config.candidates.map((c) => c.name);

  const [fatigueRate, setFatigueRate] = useState(0.07);
  const [engagedPct, setEngagedPct] = useState(0.2);
  const [numElections, setNumElections] = useState(8);
  const sim = $api.useMutation('post', '/api/v2/election/electoral-fatigue');
  const data: FatigueData | null = (sim.data as FatigueData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('fatigue.error') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (fr: number, ep: number, ne: number) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          num_elections: ne,
          fatigue_rate: fr,
          engaged_voter_pct: ep,
          method: 'plurality',
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(fatigueRate, engagedPct, numElections);

  const schedule = useCallback(
    (fr: number, ep: number, ne: number) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => runSimulation(fr, ep, ne), DEBOUNCE_MS);
    },
    [runSimulation]
  );

  const hasData = data !== null;
  useEffect(() => {
    if (!hasData) return;
    schedule(fatigueRate, engagedPct, numElections);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fatigueRate, engagedPct, numElections]);

  // ── Chart data ──────────────────────────────────────────────────────────
  const lineData =
    data?.elections.map((e) => ({
      election: e.election_n,
      turnout: Math.round(e.turnout * 100),
      ideology: Math.round(e.voter_profile.mean_ideology_x * 100) / 100,
      partisan: Math.round(e.voter_profile.partisan_pct * 100),
    })) ?? [];

  const areaData =
    data?.elections.map((e) => ({
      election: e.election_n,
      ...Object.fromEntries(
        candidateNames.map((c) => [c, Math.round((e.vote_shares[c] ?? 0) * 100)])
      ),
    })) ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('fatigue.fatigueRate')}: <strong>{Math.round(fatigueRate * 100)}%</strong>
          </label>
          <Range
            data-testid="fatigue-rate-slider"
            min={0}
            max={0.15}
            step={0.01}
            value={fatigueRate}
            onChange={(e) => setFatigueRate(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('fatigue.engagedPct')}: <strong>{Math.round(engagedPct * 100)}%</strong>
          </label>
          <Range
            data-testid="engaged-slider"
            min={0.05}
            max={0.5}
            step={0.05}
            value={engagedPct}
            onChange={(e) => setEngagedPct(Number(e.target.value))}
          />
        </Col>
        <Col xs={6} md={2}>
          <label className="mb-1 inline-block text-sm mb-0">{t('fatigue.numElections')}</label>
          <Control
            type="number"
            size="sm"
            min={2}
            max={12}
            value={numElections}
            onChange={(e) => setNumElections(Math.max(2, Math.min(12, Number(e.target.value))))}
          />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}>
            {loading ? <Spinner size="sm" /> : t('fatigue.run')}
          </Button>
        </Col>
        {data && (
          <Col xs="auto">
            <PinToCentralButton
              type="fatigue"
              icon="😴"
              label={t('fatigue.run')}
              summary={
                data.winner_changed_at != null
                  ? `${t('fatigue.winnerChangedAt')} E${data.winner_changed_at}`
                  : `${data.winner_drift[0] ?? '—'} → ${data.winner_drift[data.winner_drift.length - 1] ?? '—'}`
              }
              methodsChanged={data.winner_changed_at != null ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('fatigue.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge
              variant={
                Math.abs(data.ideology_drift) > 0.1
                  ? 'danger'
                  : Math.abs(data.ideology_drift) > 0.03
                    ? 'warning'
                    : 'secondary'
              }
              data-testid="ideology-drift-badge"
            >
              {t('fatigue.ideologyDrift')}: {data.ideology_drift >= 0 ? '+' : ''}
              {data.ideology_drift.toFixed(3)}
            </Badge>
            <Badge variant="info" data-testid="rep-gap-badge">
              {t('fatigue.repGap')}: {data.representation_gap >= 0 ? '+' : ''}
              {data.representation_gap.toFixed(3)}
            </Badge>
            <Badge variant="secondary" data-testid="final-turnout-badge">
              {t('fatigue.finalTurnout')}: {Math.round((data.elections.at(-1)?.turnout ?? 0) * 100)}
              %
            </Badge>
            {data.winner_changed_at != null && (
              <Badge variant="danger" data-testid="winner-changed-badge">
                {t('fatigue.winnerChangedAt')} E{data.winner_changed_at}
              </Badge>
            )}
          </div>

          {/* Turnout + ideology LineChart */}
          <div className="mb-4" data-testid="turnout-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('fatigue.turnoutTitle')}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={lineData} margin={{ top: 4, right: 32, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="election"
                  label={{
                    value: t('fatigue.electionN'),
                    position: 'insideBottom',
                    offset: -2,
                    fontSize: 10,
                  }}
                />
                <YAxis yAxisId="left" domain={[0, 100]} unit="%" tick={{ fontSize: 10 }} />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[-1, 1]}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <ReferenceLine
                  yAxisId="right"
                  y={data.full_mean_ideology}
                  stroke="#6c757d"
                  strokeDasharray="4 2"
                  label={{ value: 'μ élect.', fill: '#6c757d', fontSize: 9 }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="turnout"
                  name={t('fatigue.turnout')}
                  stroke="#005CAB"
                  strokeWidth={2}
                  dot
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="ideology"
                  name={t('fatigue.ideology')}
                  stroke="#C8590A"
                  strokeWidth={2}
                  dot
                  strokeDasharray="4 2"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Vote share AreaChart */}
          <div className="mb-4" data-testid="area-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('fatigue.areaTitle')}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart
                data={areaData}
                margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
                stackOffset="expand"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="election" tick={{ fontSize: 10 }} />
                <YAxis
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {candidateNames.map((c, i) => (
                  <Area
                    key={c}
                    type="monotone"
                    dataKey={c}
                    stackId="1"
                    fill={candColor(c, candidateNames)}
                    stroke={candColor(c, candidateNames)}
                    fillOpacity={0.7}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Voter composition bars */}
          <VoterCompositionBars elections={data.elections} t={t} />

          {/* Winner drift */}
          <div className="flex flex-wrap gap-1 mb-3" data-testid="winner-drift-badges">
            {data.elections.map((e, i) => (
              <Badge
                key={i}
                style={{
                  background: candColor(e.winner ?? '', candidateNames),
                  fontSize: '0.7rem',
                }}
              >
                E{e.election_n}: {e.winner}
              </Badge>
            ))}
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('fatigue.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default ElectoralFatiguePanel;
