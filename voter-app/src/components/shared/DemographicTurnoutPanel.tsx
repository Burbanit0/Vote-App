/**
 * DemographicTurnoutPanel — simulates the distortion between the real
 * electorate (full population) and the effective electorate (those who vote)
 * due to differential turnout across demographic groups.
 */
import React, { useCallback, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoterProfile {
  mean_age_group: number;
  mean_education_level: number;
  mean_ideology_x: number;
}
interface ElectionResult {
  winner: string | null;
  vote_shares: Record<string, number>;
  actual_turnout?: number;
  voter_profile?: VoterProfile;
  mean_ideology_x?: number;
  winners_by_method?: Record<string, string | null>;
}
interface BreakdownEntry {
  group: string;
  population_pct: number;
  voter_pct: number;
  ideology_mean: number;
}
interface DemoData {
  biased_result: ElectionResult;
  corrected_result: ElectionResult;
  winner_changed: boolean;
  representation_gap: {
    ideology_drift: number;
    overrepresented_groups: string[];
    underrepresented_groups: string[];
  };
  demographic_breakdown: BreakdownEntry[];
  pedagogical_note: string;
}

// ── Preset profiles ───────────────────────────────────────────────────────────

interface DemoProfile {
  label: string;
  age_distribution: number[];
  turnout_by_age: number[];
  ideology_by_age: number[];
  education_distribution: number[];
  turnout_by_education: number[];
  ideology_by_education: number[];
}

const PROFILES: Record<string, DemoProfile> = {
  france_2022: {
    label: 'France 2022',
    age_distribution: [0.25, 0.45, 0.3],
    turnout_by_age: [0.55, 0.7, 0.85],
    ideology_by_age: [-0.15, 0.0, 0.15],
    education_distribution: [0.35, 0.65],
    turnout_by_education: [1.0, 1.0],
    ideology_by_education: [0.1, -0.05],
  },
  usa_2020: {
    label: 'USA 2020',
    age_distribution: [0.22, 0.48, 0.3],
    turnout_by_age: [0.54, 0.65, 0.76],
    ideology_by_age: [-0.2, 0.0, 0.25],
    education_distribution: [0.4, 0.6],
    turnout_by_education: [1.0, 1.0],
    ideology_by_education: [0.15, -0.1],
  },
  sweden_2022: {
    label: 'Suède 2022',
    age_distribution: [0.2, 0.5, 0.3],
    turnout_by_age: [0.75, 0.85, 0.88],
    ideology_by_age: [-0.1, 0.0, 0.1],
    education_distribution: [0.25, 0.75],
    turnout_by_education: [1.0, 1.0],
    ideology_by_education: [0.05, -0.05],
  },
  uk_2019: {
    label: 'UK 2019',
    age_distribution: [0.22, 0.45, 0.33],
    turnout_by_age: [0.48, 0.61, 0.74],
    ideology_by_age: [-0.25, 0.0, 0.3],
    education_distribution: [0.42, 0.58],
    turnout_by_education: [1.0, 1.0],
    ideology_by_education: [0.2, -0.15],
  },
};

// ── Ideology drift SVG ────────────────────────────────────────────────────────

const DRIFT_W = 400,
  DRIFT_H = 60,
  DRIFT_PAD = 30;

interface DriftProps {
  fullMean: number;
  biasedMean: number;
  threshold: number;
}

const IdeologyDriftSVG: React.FC<DriftProps> = ({ fullMean, biasedMean }) => {
  const pct = (x: number) => DRIFT_PAD + ((x + 1) / 2) * (DRIFT_W - 2 * DRIFT_PAD);
  return (
    <svg data-testid="ideology-drift-svg" width="100%" viewBox={`0 0 ${DRIFT_W} ${DRIFT_H}`}>
      {/* Axis */}
      <line
        x1={DRIFT_PAD}
        y1={DRIFT_H / 2}
        x2={DRIFT_W - DRIFT_PAD}
        y2={DRIFT_H / 2}
        stroke="#dee2e6"
        strokeWidth={2}
      />
      <text
        x={DRIFT_PAD}
        y={DRIFT_H - 4}
        textAnchor="middle"
        style={{ fontSize: 9, fill: '#6c757d' }}
      >
        G
      </text>
      <text
        x={DRIFT_W - DRIFT_PAD}
        y={DRIFT_H - 4}
        textAnchor="middle"
        style={{ fontSize: 9, fill: '#6c757d' }}
      >
        D
      </text>
      {/* Full population mean */}
      <line
        x1={pct(fullMean)}
        y1={8}
        x2={pct(fullMean)}
        y2={DRIFT_H - 12}
        stroke="#adb5bd"
        strokeWidth={2}
        strokeDasharray="4 2"
      />
      <text x={pct(fullMean)} y={7} textAnchor="middle" style={{ fontSize: 8, fill: '#6c757d' }}>
        Population
      </text>
      {/* Biased mean */}
      <line
        x1={pct(biasedMean)}
        y1={8}
        x2={pct(biasedMean)}
        y2={DRIFT_H - 12}
        stroke="#dc3545"
        strokeWidth={2}
      />
      <text x={pct(biasedMean)} y={7} textAnchor="middle" style={{ fontSize: 8, fill: '#dc3545' }}>
        Votants
      </text>
    </svg>
  );
};

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22', '#e83e8c'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Main panel ────────────────────────────────────────────────────────────────

const DemographicTurnoutPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();
  const candidateNames = config.candidates.map((c) => c.name);

  const [preset, setPreset] = useState('france_2022');
  const [profile, setProfile] = useState<DemoProfile>(PROFILES.france_2022);
  const sim = $api.useMutation('post', '/api/v2/election/demographic-turnout');
  const data: DemoData | null = (sim.data as DemoData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('demo.error') : null;

  const applyPreset = (key: string) => {
    setPreset(key);
    setProfile(PROFILES[key] ?? PROFILES.france_2022);
  };

  const runSimulation = useCallback(
    (p: DemoProfile) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          seed: config.seed,
          method: 'plurality',
          correct_for_turnout: true,
          demographic_profile: {
            age_distribution: p.age_distribution,
            turnout_by_age: p.turnout_by_age,
            ideology_by_age: p.ideology_by_age,
            education_distribution: p.education_distribution,
            turnout_by_education: p.turnout_by_education,
            ideology_by_education: p.ideology_by_education,
          },
        },
      });
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(profile);

  // ── Chart data ──────────────────────────────────────────────────────────
  const pyramidData =
    data?.demographic_breakdown.map((d) => ({
      group: d.group.length > 22 ? d.group.slice(0, 20) + '…' : d.group,
      population: Math.round(d.population_pct * 100),
      voters: Math.round(d.voter_pct * 100),
    })) ?? [];

  const biasedBarData = candidateNames.map((c) => ({
    name: c,
    share: Math.round((data?.biased_result.vote_shares[c] ?? 0) * 100),
  }));

  const correctedBarData = candidateNames.map((c) => ({
    name: c,
    share: Math.round((data?.corrected_result.vote_shares[c] ?? 0) * 100),
  }));

  return (
    <div>
      {/* Preset selector */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">{t('demo.preset')}</label>
          <Select
            size="sm"
            value={preset}
            data-testid="preset-select"
            onChange={(e) => applyPreset(e.target.value)}
          >
            {Object.entries(PROFILES).map(([key, p]) => (
              <option key={key} value={key}>
                {p.label}
              </option>
            ))}
          </Select>
        </Col>
        <Col xs={12} md={6}>
          <div className="flex flex-wrap gap-1" style={{ fontSize: '0.72rem' }}>
            {['jeunes', 'adultes', 'seniors'].map((ag, i) => (
              <div key={ag} className="border border-border rounded px-2 py-1">
                <span className="text-muted-foreground">{ag}: </span>
                <strong>{Math.round(profile.turnout_by_age[i] * 100)}%</strong>
              </div>
            ))}
          </div>
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            onClick={handleSimulate}
            disabled={loading}
            data-testid="simulate-btn"
          >
            {loading ? <Spinner size="sm" /> : t('demo.run')}
          </Button>
        </Col>
        {data &&
          (() => {
            const bbm = data.biased_result.winners_by_method ?? {};
            const cbm = data.corrected_result.winners_by_method ?? {};
            let changedCount = 0;
            Object.entries(bbm).forEach(([m, w]) => {
              if (w !== cbm[m]) changedCount += 1;
            });
            if (changedCount === 0 && data.winner_changed) changedCount = 1;
            return (
              <Col xs="auto">
                <PinToCentralButton
                  type="demographic"
                  icon="👥"
                  label={t('demo.run')}
                  summary={
                    changedCount > 0
                      ? `${changedCount}/${Object.keys(bbm).length || 1} ${t('lab.methodsChanged')}`
                      : `${t('demo.biasedWinner')}: ${data.biased_result.winner}`
                  }
                  methodsChanged={changedCount}
                  winnersByMethod={data.biased_result.winners_by_method}
                />
              </Col>
            );
          })()}
      </Row>

      {/* Turnout sliders */}
      <Row className="g-2 mb-3">
        {['jeunes (18-34)', 'adultes (35-64)', 'seniors (65+)'].map((ag, i) => (
          <Col key={ag} xs={4}>
            <label className="mb-1 inline-block text-sm mb-0" style={{ fontSize: '0.72rem' }}>
              {ag}: <strong>{Math.round(profile.turnout_by_age[i] * 100)}%</strong>
            </label>
            <Range
              data-testid={`turnout-slider-${i}`}
              min={0}
              max={1}
              step={0.05}
              value={profile.turnout_by_age[i]}
              onChange={(e) => {
                const next = [...profile.turnout_by_age];
                next[i] = Number(e.target.value);
                setProfile({ ...profile, turnout_by_age: next });
              }}
            />
          </Col>
        ))}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('demo.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="primary" data-testid="biased-winner-badge">
              {t('demo.biasedWinner')}: {data.biased_result.winner}
            </Badge>
            {data.winner_changed && (
              <>
                <Badge variant="success" data-testid="corrected-winner-badge">
                  {t('demo.correctedWinner')}: {data.corrected_result.winner}
                </Badge>
                <Alert
                  variant="danger"
                  className="inline-block py-1 px-2 mb-0"
                  data-testid="winner-changed-alert"
                >
                  {t('demo.winnerChanged')}
                </Alert>
              </>
            )}
            <Badge
              variant={
                Math.abs(data.representation_gap.ideology_drift) > 0.1 ? 'danger' : 'secondary'
              }
              data-testid="drift-badge"
            >
              {t('demo.drift')}: {data.representation_gap.ideology_drift >= 0 ? '+' : ''}
              {data.representation_gap.ideology_drift.toFixed(3)}
            </Badge>
            <Badge variant="info" data-testid="turnout-badge">
              {t('demo.turnout')}: {Math.round(data.biased_result.actual_turnout! * 100)}%
            </Badge>
          </div>

          {/* Ideology drift visualisation */}
          <div className="mb-3">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('demo.ideologyTitle')}
            </div>
            <IdeologyDriftSVG
              fullMean={data.corrected_result.mean_ideology_x ?? 0}
              biasedMean={data.biased_result.voter_profile?.mean_ideology_x ?? 0}
              threshold={0}
            />
          </div>

          {/* Double pyramid (population vs voters) */}
          <div className="mb-4" data-testid="pyramid-chart">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('demo.pyramidTitle')}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={pyramidData}
                layout="vertical"
                margin={{ top: 4, right: 16, bottom: 4, left: 120 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" unit="%" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="group" tick={{ fontSize: 9 }} width={118} />
                <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar
                  dataKey="population"
                  name={t('demo.population')}
                  fill="#adb5bd"
                  opacity={0.6}
                />
                <Bar dataKey="voters" name={t('demo.voters')} fill="#005CAB" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Dual BarChart comparison */}
          <Row className="g-3 mb-4">
            <Col xs={6}>
              <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('demo.biasedResult')}
              </div>
              <div data-testid="biased-bar-chart">
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={biasedBarData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis unit="%" tick={{ fontSize: 10 }} domain={[0, 60]} />
                    <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                    <Bar dataKey="share">
                      {biasedBarData.map((entry, i) => (
                        <Cell key={i} fill={candColor(entry.name, candidateNames)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Col>
            <Col xs={6}>
              <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('demo.correctedResult')}
              </div>
              <div data-testid="corrected-bar-chart">
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart
                    data={correctedBarData}
                    margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
                  >
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis unit="%" tick={{ fontSize: 10 }} domain={[0, 60]} />
                    <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                    <Bar dataKey="share">
                      {correctedBarData.map((entry, i) => (
                        <Cell key={i} fill={candColor(entry.name, candidateNames)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Col>
          </Row>

          {/* Demographic breakdown table */}
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50 mb-3"
            data-testid="breakdown-table"
          >
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('demo.group')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('demo.popPct')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('demo.voterPct')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('demo.ideology')}</th>
              </tr>
            </thead>
            <tbody>
              {data.demographic_breakdown.map((d) => {
                const over = d.voter_pct > d.population_pct + 0.05;
                const under = d.voter_pct < d.population_pct - 0.05;
                return (
                  <tr
                    key={d.group}
                    style={{ background: over ? '#f0fff4' : under ? '#fff5f5' : undefined }}
                  >
                    <td style={{ fontSize: '0.78rem' }}>{d.group}</td>
                    <td style={{ fontSize: '0.78rem' }}>{Math.round(d.population_pct * 100)}%</td>
                    <td
                      style={{
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: over ? '#198754' : under ? '#dc3545' : undefined,
                      }}
                    >
                      {Math.round(d.voter_pct * 100)}%{over && ' ▲'}
                      {under && ' ▼'}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {d.ideology_mean >= 0 ? '+' : ''}
                      {d.ideology_mean.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('demo.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default DemographicTurnoutPanel;
