/**
 * AffectivePolarizationPanel — models how inter-partisan hostility
 * distorts voting utilities and destabilises election results.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { $api } from '../../api/hooks';

const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface VoterSnap {
  id: number;
  x: number;
  y: number;
  camp: string;
  sincere_pref: string;
  affective_pref: string;
}

interface AffectData {
  sincere_results: Record<string, string | null>;
  affective_results: Record<string, string | null>;
  winner_changed: boolean;
  condorcet_violation: boolean;
  sincere_cw: string | null;
  affective_cw: string | null;
  method_sensitivity: Record<string, number>;
  affect_curve: { hostility: number; condorcet_rate: number; agreement_rate: number }[];
  candidate_camps: Record<string, string>;
  voters: VoterSnap[];
  candidates: { name: string; x: number }[];
  pedagogical_note: string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAMP_COLOR: Record<string, string> = {
  left: '#005CAB',
  right: '#C8590A',
  centre: '#007A33',
};

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]) {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── SVG ideology overlay ──────────────────────────────────────────────────────

const SVG_W = 360;
const SVG_H = 300;
const PAD = 20;
function dx(v: number) {
  return PAD + ((v + 1) / 2) * (SVG_W - 2 * PAD);
}
function dy(v: number) {
  return PAD + ((1 - v) / 2) * (SVG_H - 2 * PAD);
}

interface OverlayProps {
  data: AffectData;
  hostility: number;
}

const IdeologyOverlay: React.FC<OverlayProps> = ({ data, hostility }) => {
  const [hovered, setHovered] = useState<VoterSnap | null>(null);
  const [tipPos, setTipPos] = useState({ x: 0, y: 0 });

  const candNames = data.candidates.map((c) => c.name);

  return (
    <div style={{ position: 'relative' }}>
      <svg
        data-testid="affect-map-svg"
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        width="100%"
        style={{ maxHeight: 280, display: 'block', userSelect: 'none' }}
      >
        {/* Axes */}
        <line
          x1={SVG_W / 2}
          y1={PAD}
          x2={SVG_W / 2}
          y2={SVG_H - PAD}
          stroke="#dee2e6"
          strokeWidth={1}
        />
        <line
          x1={PAD}
          y1={SVG_H / 2}
          x2={SVG_W - PAD}
          y2={SVG_H / 2}
          stroke="#dee2e6"
          strokeWidth={1}
        />
        <rect
          x={PAD}
          y={PAD}
          width={SVG_W - 2 * PAD}
          height={SVG_H - 2 * PAD}
          fill="none"
          stroke="#ced4da"
          strokeWidth={0.8}
        />
        <text x={PAD} y={SVG_H - 5} fontSize={8} fill="#adb5bd">
          ← Gauche
        </text>
        <text x={SVG_W - PAD} y={SVG_H - 5} textAnchor="end" fontSize={8} fill="#adb5bd">
          Droite →
        </text>

        {/* Voter dots — sincere behind, affective in front */}
        {data.voters.map((v) => {
          const sx = dx(v.x);
          const sy = dy(v.y);
          const camp = v.camp;
          const changed = v.sincere_pref !== v.affective_pref;
          return (
            <g key={v.id}>
              {/* Sincere (ghost) */}
              <circle
                cx={sx}
                cy={sy}
                r={2.5}
                fill={CAMP_COLOR[camp] ?? '#888'}
                fillOpacity={0.15}
                style={{ pointerEvents: 'none' }}
              />
              {/* Affective */}
              <circle
                cx={sx}
                cy={sy}
                r={changed ? 3.5 : 2.5}
                fill={changed ? '#dc3545' : (CAMP_COLOR[camp] ?? '#888')}
                fillOpacity={0.5 + hostility * 0.4}
                stroke={changed ? '#dc3545' : 'none'}
                strokeWidth={changed ? 0.5 : 0}
                data-testid={changed ? 'changed-voter' : 'unchanged-voter'}
                onMouseEnter={(e) => {
                  setHovered(v);
                  setTipPos({ x: e.clientX, y: e.clientY });
                }}
                onMouseLeave={() => setHovered(null)}
              />
            </g>
          );
        })}

        {/* Candidate ★ markers */}
        {data.candidates.map((c) => {
          const cx = dx(c.x);
          const cy = SVG_H / 2;
          const color = candColor(c.name, candNames);
          const camp = data.candidate_camps[c.name] ?? 'centre';
          return (
            <g key={c.name}>
              <text
                cx={cx}
                cy={cy}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={18}
                fill={color}
                stroke="#fff"
                strokeWidth={0.6}
                x={cx}
                y={cy}
                style={{ userSelect: 'none', pointerEvents: 'none' }}
              >
                ★
              </text>
              <text
                x={cx}
                y={cy - 16}
                textAnchor="middle"
                fontSize={9}
                fontWeight={600}
                fill={color}
                stroke="#fff"
                strokeWidth={2.5}
                paintOrder="stroke"
                style={{ pointerEvents: 'none' }}
              >
                {c.name} [{camp[0].toUpperCase()}]
              </text>
            </g>
          );
        })}
      </svg>

      {hovered && (
        <div
          style={{
            position: 'fixed',
            left: tipPos.x + 10,
            top: tipPos.y - 10,
            background: 'rgba(0,0,0,0.82)',
            color: '#fff',
            padding: '4px 8px',
            borderRadius: 5,
            fontSize: '0.72rem',
            zIndex: 9000,
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          Camp: {hovered.camp} · Sincère: {hovered.sincere_pref}
          {hovered.sincere_pref !== hovered.affective_pref && (
            <span style={{ color: '#ff6b6b' }}> → Affectif: {hovered.affective_pref}</span>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const AffectivePolarizationPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [hostility, setHostility] = useState(0.5);
  const [numSims, setNumSims] = useState(15);
  const sim = $api.useMutation('post', '/api/v2/election/affective-polarization');
  const data: AffectData | null = (sim.data as AffectData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('affect.error') : null;

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const run = useCallback(
    (h: number, sims: number) => {
      sim.mutate({
        body: {
          candidates: config.candidates,
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          affect_hostility: h,
          camp_threshold: 0.1,
          num_simulations: sims,
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [config, t, sim]
  );

  const handleHostilityChange = (v: number) => {
    setHostility(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(v, numSims), DEBOUNCE_MS);
  };

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    },
    []
  );

  const candNames = data?.candidates.map((c) => c.name) ?? [];
  const allMethods = data ? Object.keys(data.sincere_results) : [];

  const changedMethods = data
    ? allMethods.filter((m) => data.sincere_results[m] !== data.affective_results[m])
    : [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} sm={5}>
          <label className="mb-1 inline-block font-semibold mb-0" style={{ fontSize: '0.85rem' }}>
            {t('affect.hostilitySlider')}: <strong>{Math.round(hostility * 100)}%</strong>
            {loading && <Spinner size="sm" className="ms-2" />}
          </label>
          <Range
            min={0}
            max={1}
            step={0.05}
            value={hostility}
            onChange={(e) => handleHostilityChange(Number(e.target.value))}
            data-testid="hostility-slider"
          />
          <div
            className="flex justify-between"
            style={{ fontSize: '0.68rem', color: '#6c757d', marginTop: -4 }}
          >
            <span>0% — Vote sincère</span>
            <span>100% — Vote tribal strict</span>
          </div>
        </Col>
        <Col xs={12} sm={3}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('affect.numSims')}: <strong>{numSims}</strong>
          </label>
          <Range
            min={5}
            max={30}
            step={5}
            value={numSims}
            onChange={(e) => setNumSims(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} sm={4}>
          <Button
            variant="primary"
            className="w-full"
            onClick={() => run(hostility, numSims)}
            disabled={loading}
          >
            {loading ? <Spinner size="sm" /> : `💔 ${t('affect.run')}`}
          </Button>
        </Col>
        {data && (
          <Col xs={12} sm="auto">
            <PinToCentralButton
              type="affective"
              icon="💔"
              label={`${t('affect.run')} — hostilité ${Math.round(hostility * 100)}%`}
              summary={
                data.winner_changed
                  ? `${changedMethods.length}/${allMethods.length} ${t('affect.methodsChanged')}`
                  : t('affect.winnerUnchanged')
              }
              methodsChanged={changedMethods.length}
              winnersByMethod={data.affective_results}
            />
          </Col>
        )}
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('affect.prompt')}</Alert>}

      {data && (
        <>
          {/* Summary badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge
              variant={data.winner_changed ? 'danger' : 'success'}
              data-testid="winner-changed-badge"
            >
              {data.winner_changed
                ? `⚠ ${t('affect.winnerChanged')}`
                : `✓ ${t('affect.winnerUnchanged')}`}
            </Badge>
            {data.condorcet_violation && (
              <Badge variant="warning" data-testid="condorcet-violation-badge">
                ✗ {t('affect.condorcetViolation')}
              </Badge>
            )}
            <Badge variant="secondary" style={{ fontSize: '0.7rem' }}>
              {changedMethods.length}/{allMethods.length} {t('affect.methodsChanged')}
            </Badge>
          </div>

          {/* Pedagogical note */}
          <Alert
            variant={data.winner_changed ? 'warning' : 'success'}
            className="py-2 mb-3"
            style={{ fontSize: '0.82rem' }}
          >
            {data.pedagogical_note}
          </Alert>

          <Row className="g-3">
            {/* Left: ideology map */}
            <Col xs={12} lg={6}>
              <div className="border border-border rounded p-2">
                <div className="text-sm font-semibold mb-1">
                  {t('affect.mapTitle')}
                  <span className="text-muted-foreground ms-2" style={{ fontWeight: 400 }}>
                    {t('affect.mapHint')}
                  </span>
                </div>
                <IdeologyOverlay data={data} hostility={hostility} />
                <div className="flex flex-wrap gap-2 mt-1" style={{ fontSize: '0.7rem' }}>
                  {(['left', 'right', 'centre'] as const).map((camp) => (
                    <span key={camp} className="flex items-center gap-1">
                      <span
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          background: CAMP_COLOR[camp],
                          display: 'inline-block',
                          opacity: 0.7,
                        }}
                      />
                      {t(`affect.camp_${camp}`)}
                    </span>
                  ))}
                  <span className="flex items-center gap-1">
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: '#dc3545',
                        display: 'inline-block',
                      }}
                    />
                    {t('affect.changedVote')}
                  </span>
                </div>
              </div>
            </Col>

            {/* Right: affect curve */}
            <Col xs={12} lg={6}>
              <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('affect.curveTitle')}
              </div>
              <div style={{ height: 220 }} data-testid="affect-curve-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={data.affect_curve}
                    margin={{ top: 8, right: 16, bottom: 16, left: -8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                    <XAxis
                      dataKey="hostility"
                      type="number"
                      domain={[0, 1]}
                      tickFormatter={(v) => `${Math.round(v * 100)}%`}
                      tick={{ fontSize: 10 }}
                    ></XAxis>
                    <YAxis
                      domain={[0, 1]}
                      tickFormatter={(v) => `${Math.round(v * 100)}%`}
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                    <Legend wrapperStyle={{ fontSize: '0.72rem' }} />
                    <ReferenceLine x={hostility} stroke="#adb5bd" strokeDasharray="3 2" />
                    <Line
                      type="monotone"
                      dataKey="condorcet_rate"
                      name={t('affect.condorcetRate')}
                      stroke="#007A33"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      isAnimationActive={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="agreement_rate"
                      name={t('affect.agreementRate')}
                      stroke="#005CAB"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Col>
          </Row>

          {/* Method sensitivity table */}
          <div className="mt-3">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('affect.methodTableTitle')}
            </div>
            <Table
              className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border"
              style={{ fontSize: '0.78rem' }}
            >
              <thead className="table-light">
                <tr>
                  <th>{t('common.method')}</th>
                  <th>{t('affect.sincereWinner')}</th>
                  <th>{t('affect.affectiveWinner')}</th>
                  <th className="text-center">{t('affect.sensitivity')}</th>
                </tr>
              </thead>
              <tbody>
                {allMethods
                  .sort(
                    (a, b) => (data.method_sensitivity[b] ?? 0) - (data.method_sensitivity[a] ?? 0)
                  )
                  .map((m) => {
                    const sens = data.method_sensitivity[m] ?? 0;
                    const changed = data.sincere_results[m] !== data.affective_results[m];
                    return (
                      <tr key={m} style={{ background: changed ? '#fff3f3' : undefined }}>
                        <td className="font-semibold" style={{ fontSize: '0.75rem' }}>
                          {m}
                        </td>
                        <td>
                          <Badge
                            style={{
                              background: candColor(data.sincere_results[m] ?? '', candNames),
                              fontSize: '0.7rem',
                            }}
                          >
                            {data.sincere_results[m] ?? '—'}
                          </Badge>
                        </td>
                        <td>
                          <Badge
                            style={{
                              background: candColor(data.affective_results[m] ?? '', candNames),
                              fontSize: '0.7rem',
                              opacity: changed ? 1 : 0.6,
                            }}
                          >
                            {data.affective_results[m] ?? '—'}
                            {changed && ' ✗'}
                          </Badge>
                        </td>
                        <td className="text-center">
                          <div
                            style={{
                              display: 'inline-block',
                              width: 60,
                              height: 8,
                              background: '#e9ecef',
                              borderRadius: 4,
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                width: `${sens * 100}%`,
                                height: '100%',
                                background:
                                  sens > 0.3 ? '#dc3545' : sens > 0.1 ? '#f0c040' : '#28a745',
                              }}
                            />
                          </div>
                          <span className="ms-1" style={{ fontSize: '0.7rem' }}>
                            {Math.round(sens * 100)}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
};

export default AffectivePolarizationPanel;
