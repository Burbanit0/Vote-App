/**
 * DemocraticBackslidingPanel — simulates the path toward autocracy.
 * Based on democratic backsliding research (Levitsky & Ziblatt, 2018).
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check, Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ElectionResult {
  election_n: number;
  winner: string;
  vote_shares: Record<string, number>;
  democratic_quality: number;
  advantages: {
    gerrymandering_bonus: number;
    media_bias: number;
    suppression_rate: number;
  };
  guardrails_triggered: string[];
  point_of_no_return: boolean;
}

interface BackslidingData {
  elections: ElectionResult[];
  autocracy_reached: boolean;
  autocracy_at_election: number | null;
  guardrails_effectiveness: Record<string, number>;
  tipping_points: number[];
  pedagogical_note: string;
}

type Method = 'gerrymandering' | 'media_capture' | 'voter_suppression';
type Guardrail =
  | 'constitutional_court'
  | 'opposition_media'
  | 'international_pressure'
  | 'supermajority_required';

const GUARDRAILS: Guardrail[] = [
  'constitutional_court',
  'opposition_media',
  'international_pressure',
  'supermajority_required',
];

// Historical reference curves
const HISTORICAL: Record<string, { label: string; color: string; data: number[] }> = {
  hungary: {
    label: '🇭🇺 Hongrie (Orbán 2010→2022)',
    color: '#fd7e14',
    data: [0.87, 0.81, 0.76, 0.71, 0.67, 0.63, 0.59, 0.54],
  },
  turkey: {
    label: '🇹🇷 Turquie (Erdoğan 2002→2022)',
    color: '#6f42c1',
    data: [0.75, 0.71, 0.65, 0.6, 0.55, 0.5, 0.46, 0.41],
  },
  venezuela: {
    label: '🇻🇪 Venezuela (1998→2023)',
    color: '#dc3545',
    data: [0.71, 0.62, 0.52, 0.42, 0.33, 0.25, 0.2, 0.15],
  },
};

// ── Quality thermometer bar ───────────────────────────────────────────────────

function qualityColor(q: number): string {
  if (q > 0.75) return '#198754';
  if (q > 0.55) return '#ffc107';
  if (q > 0.35) return '#fd7e14';
  return '#dc3545';
}

const QualityBar: React.FC<{ value: number }> = ({ value }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <div
      style={{
        flex: 1,
        height: 12,
        background: '#dee2e6',
        borderRadius: 6,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.round(value * 100)}%`,
          height: '100%',
          background: qualityColor(value),
          transition: 'width 0.3s',
        }}
      />
    </div>
    <span
      style={{ fontSize: '0.75rem', fontWeight: 700, color: qualityColor(value), minWidth: 36 }}
    >
      {Math.round(value * 100)}%
    </span>
  </div>
);

// ── Main panel ────────────────────────────────────────────────────────────────

const DemocraticBackslidingPanel: React.FC = () => {
  const { t } = useTranslation();

  const sim = $api.useMutation('post', '/api/v2/theory/democratic-backsliding');
  const data: BackslidingData | null = (sim.data as BackslidingData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('backsliding.error') : null;
  const [numVoters, setNumVoters] = useState(200);
  const [numElections, setNumElections] = useState(8);
  const [seed, setSeed] = useState(42);
  const [method, setMethod] = useState<Method>('gerrymandering');
  const [intensity, setIntensity] = useState(0.6);
  const [guardrails, setGuardrails] = useState<Record<Guardrail, boolean>>({
    constitutional_court: false,
    opposition_media: false,
    international_pressure: false,
    supermajority_required: false,
  });
  const [showHistorical, setShowHistorical] = useState<string[]>([]);

  const run = useCallback(
    (grOverride?: Record<Guardrail, boolean>) => {
      const gr = grOverride ?? guardrails;
      sim.mutate({
        body: {
          candidates: [
            { name: t('backsliding.incumbent'), x: 0.2, y: 0.0 },
            { name: t('backsliding.opposition'), x: -0.4, y: 0.0 },
          ],
          num_voters: numVoters,
          ideology: 'random',
          seed,
          num_elections: numElections,
          backsliding_method: method,
          backsliding_intensity: intensity,
          guardrails: gr,
        },
      });
    },
    [guardrails, numVoters, seed, numElections, method, intensity, t, sim]
  );

  const handleGuardrailToggle = (gr: Guardrail) => {
    const updated = { ...guardrails, [gr]: !guardrails[gr] };
    setGuardrails(updated);
    if (data) run(updated);
  };

  // ── Chart data ─────────────────────────────────────────────────────────────
  const chartData = data
    ? data.elections.map((e) => {
        const pt: Record<string, number | string> = {
          n: e.election_n,
          quality: e.democratic_quality,
        };
        showHistorical.forEach((hk) => {
          const hist = HISTORICAL[hk];
          if (hist && e.election_n <= hist.data.length) {
            pt[hk] = hist.data[e.election_n - 1];
          }
        });
        return pt;
      })
    : [];

  const finalQuality = data ? data.elections[data.elections.length - 1].democratic_quality : null;

  return (
    <div>
      {/* ── Paradox quote ── */}
      <Alert
        variant="danger"
        className="py-2 mb-3"
        data-testid="paradox-quote"
        style={{ fontSize: '0.78rem', borderLeft: '4px solid #dc3545' }}
      >
        <strong>{t('backsliding.paradoxTitle')}</strong> {t('backsliding.paradox')}
      </Alert>

      {/* ── Controls ── */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={6} md={2}>
          <label className="mb-1 inline-block text-sm mb-0">{t('backsliding.voters')}</label>
          <Control
            type="number"
            size="sm"
            min={20}
            max={1000}
            value={numVoters}
            data-testid="voters-input"
            onChange={(e) => setNumVoters(Number(e.target.value))}
          />
        </Col>
        <Col xs={6} md={2}>
          <label className="mb-1 inline-block text-sm mb-0">{t('backsliding.elections')}</label>
          <Control
            type="number"
            size="sm"
            min={2}
            max={15}
            value={numElections}
            data-testid="elections-input"
            onChange={(e) => setNumElections(Number(e.target.value))}
          />
        </Col>
        <Col xs={6} md={2}>
          <label className="mb-1 inline-block text-sm mb-0">{t('backsliding.seed')}</label>
          <Control
            type="number"
            size="sm"
            value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">{t('backsliding.method')}</label>
          <Select
            size="sm"
            value={method}
            data-testid="method-select"
            onChange={(e) => setMethod(e.target.value as Method)}
          >
            <option value="gerrymandering">{t('backsliding.method_gerrymandering')}</option>
            <option value="media_capture">{t('backsliding.method_media_capture')}</option>
            <option value="voter_suppression">{t('backsliding.method_voter_suppression')}</option>
          </Select>
        </Col>
        <Col xs="auto">
          <Button
            variant="danger"
            size="sm"
            onClick={() => run()}
            disabled={loading}
            data-testid="run-btn"
          >
            {loading ? <Spinner size="sm" /> : t('backsliding.run')}
          </Button>
        </Col>
      </Row>

      {/* ── Intensity slider ── */}
      <Row className="g-2 mb-3 items-center">
        <Col xs={12} md={6}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('backsliding.intensity')} — {Math.round(intensity * 100)}%
          </label>
          <Range
            min={0}
            max={100}
            value={Math.round(intensity * 100)}
            data-testid="intensity-slider"
            onChange={(e) => setIntensity(Number(e.target.value) / 100)}
          />
        </Col>
      </Row>

      {/* ── Guardrails ── */}
      <div
        className="mb-3 border border-border rounded p-2"
        style={{ background: '#f0f8ff' }}
        data-testid="guardrails-panel"
      >
        <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
          🛡 {t('backsliding.guardrailsTitle')}
        </div>
        <Row className="g-2">
          {GUARDRAILS.map((gr) => (
            <Col key={gr} xs={12} md={6}>
              <Check
                type="switch"
                id={`gr-${gr}`}
                label={
                  <span style={{ fontSize: '0.78rem' }}>
                    {t(`backsliding.guardrail_${gr}`)}
                    {guardrails[gr] && data && (
                      <Badge variant="success" className="ms-1" style={{ fontSize: '0.6rem' }}>
                        +{Math.round((data.guardrails_effectiveness[gr] ?? 0) * 100)}%
                      </Badge>
                    )}
                  </span>
                }
                checked={guardrails[gr]}
                data-testid={`guardrail-${gr}`}
                onChange={() => handleGuardrailToggle(gr)}
              />
            </Col>
          ))}
        </Row>
      </div>

      {!data && !loading && !error && (
        <Alert variant="secondary" data-testid="prompt-alert">
          {t('backsliding.prompt')}
        </Alert>
      )}
      {error && (
        <Alert variant="danger" data-testid="error-alert">
          {error}
        </Alert>
      )}

      {data && (
        <>
          {/* ── Autocracy warning ── */}
          {data.autocracy_reached && (
            <Alert variant="danger" className="py-2 mb-3" data-testid="autocracy-alert">
              🚨 {t('backsliding.autocracyReached', { n: data.autocracy_at_election })}
            </Alert>
          )}

          {/* ── Final quality bar ── */}
          <div className="mb-3" data-testid="quality-summary">
            <div className="flex justify-between items-center mb-1">
              <span className="font-semibold" style={{ fontSize: '0.82rem' }}>
                {t('backsliding.finalQuality')}
              </span>
              <Badge
                variant={
                  finalQuality! > 0.7 ? 'success' : finalQuality! > 0.45 ? 'warning' : 'danger'
                }
              >
                {finalQuality! > 0.7
                  ? t('backsliding.statusHealthy')
                  : finalQuality! > 0.45
                    ? t('backsliding.statusEroding')
                    : t('backsliding.statusAutocratic')}
              </Badge>
            </div>
            <QualityBar value={finalQuality!} />
          </div>

          {/* ── Timeline chart ── */}
          <div className="mb-2 font-semibold" style={{ fontSize: '0.82rem' }}>
            {t('backsliding.timelineTitle')}
          </div>

          {/* Historical overlay toggles */}
          <div className="flex gap-2 flex-wrap mb-2" data-testid="historical-toggles">
            {Object.entries(HISTORICAL).map(([key, h]) => (
              <Badge
                key={key}
                style={{
                  cursor: 'pointer',
                  fontSize: '0.68rem',
                  padding: '5px 8px',
                  background: showHistorical.includes(key) ? h.color : '#dee2e6',
                  color: showHistorical.includes(key) ? '#fff' : '#495057',
                }}
                onClick={() =>
                  setShowHistorical((prev) =>
                    prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
                  )
                }
                data-testid={`hist-toggle-${key}`}
              >
                {h.label}
              </Badge>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={260} data-testid="timeline-chart">
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="n"
                label={{
                  value: t('backsliding.electionN'),
                  position: 'insideBottom',
                  offset: -5,
                  fontSize: 10,
                }}
                tick={{ fontSize: 10 }}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(v) => `${Math.round(v * 100)}%`}
                tick={{ fontSize: 10 }}
                label={{
                  value: t('backsliding.qualityAxis'),
                  angle: -90,
                  position: 'insideLeft',
                  fontSize: 10,
                }}
              />
              <ReferenceLine
                y={0.45}
                stroke="#dc3545"
                strokeDasharray="6 3"
                label={{
                  value: t('backsliding.pointOfNoReturn'),
                  fontSize: 9,
                  fill: '#dc3545',
                  position: 'right',
                }}
              />
              <Tooltip
                formatter={(v: number, name: string) => [
                  `${Math.round(v * 100)}%`,
                  name === 'quality'
                    ? t('backsliding.simulationLabel')
                    : (HISTORICAL[name]?.label ?? name),
                ]}
              />
              <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
              <Line
                type="monotone"
                dataKey="quality"
                name={t('backsliding.simulationLabel')}
                stroke="#0d6efd"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
              {showHistorical.map((hk) => (
                <Line
                  key={hk}
                  type="monotone"
                  dataKey={hk}
                  name={HISTORICAL[hk].label}
                  stroke={HISTORICAL[hk].color}
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>

          {/* ── Election timeline cards ── */}
          <div className="mt-3" data-testid="elections-timeline">
            <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
              {t('backsliding.electionsTitle')}
            </div>
            <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
              {data.elections.map((e) => {
                const q = e.democratic_quality;
                return (
                  <div
                    key={e.election_n}
                    style={{
                      minWidth: 80,
                      border: `2px solid ${qualityColor(q)}`,
                      borderRadius: 6,
                      padding: '6px 8px',
                      background: e.point_of_no_return ? '#fff3cd' : '#fff',
                      fontSize: '0.7rem',
                    }}
                    data-testid={`election-card-${e.election_n}`}
                  >
                    <div className="font-bold" style={{ color: qualityColor(q) }}>
                      #{e.election_n}
                    </div>
                    <div style={{ fontSize: '0.65rem' }}>{e.winner}</div>
                    <QualityBar value={q} />
                    {e.guardrails_triggered.length > 0 && (
                      <div style={{ fontSize: '0.6rem', color: '#198754', marginTop: 2 }}>
                        🛡×{e.guardrails_triggered.length}
                      </div>
                    )}
                    {e.point_of_no_return && (
                      <div style={{ fontSize: '0.6rem', color: '#dc3545', fontWeight: 700 }}>
                        ⚠ {t('backsliding.pnr')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── Advantages table ── */}
          <div className="mt-3" data-testid="advantages-section" style={{ fontSize: '0.75rem' }}>
            <div className="font-semibold mb-1">{t('backsliding.advantagesTitle')}</div>
            <table className="table table-sm table-bordered">
              <thead className="table-light">
                <tr>
                  <th>#</th>
                  <th>{t('backsliding.adv_gerrymander')}</th>
                  <th>{t('backsliding.adv_media')}</th>
                  <th>{t('backsliding.adv_suppression')}</th>
                  <th>{t('backsliding.qualityCol')}</th>
                </tr>
              </thead>
              <tbody>
                {data.elections.map((e) => (
                  <tr
                    key={e.election_n}
                    style={{ background: e.point_of_no_return ? '#fff3cd' : undefined }}
                    data-testid={`adv-row-${e.election_n}`}
                  >
                    <td>{e.election_n}</td>
                    <td>{Math.round(e.advantages.gerrymandering_bonus * 100)}%</td>
                    <td>{Math.round(e.advantages.media_bias * 100)}%</td>
                    <td>{Math.round(e.advantages.suppression_rate * 100)}%</td>
                    <td>
                      <span style={{ color: qualityColor(e.democratic_quality), fontWeight: 700 }}>
                        {Math.round(e.democratic_quality * 100)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert
            variant="secondary"
            className="mt-3"
            style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note"
          >
            <strong>{t('backsliding.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default DemocraticBackslidingPanel;
