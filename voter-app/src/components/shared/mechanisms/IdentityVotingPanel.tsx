/**
 * IdentityVotingPanel — identity vs ideology in voting behaviour.
 * Green, Palmquist & Schickler (2002) "Partisan Hearts and Minds".
 */
import React, { useCallback, useEffect, useState } from 'react';
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
  Legend,
  LineChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { $api } from '../../../api/hooks';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

// ── Types ─────────────────────────────────────────────────────────────────────

interface IdentityGroup {
  name: string;
  pct: number;
  ideology_center: number;
  loyalty: number;
  candidate_affiliation: string;
}

interface GroupResult {
  group_name: string;
  affiliation: string;
  group_vote_pct: number;
  ideology_match: number;
  loyalty: number;
  size_pct: number;
}

interface CurvePoint {
  weight: number;
  winner: string;
  agreement_rate: number;
}

interface IdentityData {
  sincere_winner: string;
  identity_winner: string;
  mixed_winner: string;
  winner_changed: boolean;
  group_results: GroupResult[];
  cross_pressured: { count: number; abstention_rate: number };
  identity_weight_curve: CurvePoint[];
  pedagogical_note: string;
}

// ── Colour palette for groups ─────────────────────────────────────────────────

const GROUP_COLORS = ['#0d6efd', '#dc3545', '#198754', '#fd7e14', '#6f42c1'];

// ── Winner change indicator ───────────────────────────────────────────────────

const WinnerBadge: React.FC<{ label: string; winner: string; highlight?: boolean }> = ({
  label,
  winner,
  highlight,
}) => (
  <div
    className="text-center p-2 border border-border rounded"
    style={{ background: highlight ? '#fff3cd' : '#f8f9fa', minWidth: 110 }}
  >
    <div style={{ fontSize: '0.65rem', color: '#6c757d' }}>{label}</div>
    <div
      className="font-bold"
      style={{ fontSize: '0.85rem', color: highlight ? '#856404' : '#333' }}
    >
      {winner}
    </div>
  </div>
);

// ── Main panel ────────────────────────────────────────────────────────────────

const DEFAULT_GROUPS: IdentityGroup[] = [
  {
    name: 'Groupe A',
    pct: 0.4,
    ideology_center: -0.3,
    loyalty: 0.75,
    candidate_affiliation: 'Alice',
  },
  { name: 'Groupe B', pct: 0.35, ideology_center: 0.1, loyalty: 0.6, candidate_affiliation: 'Bob' },
  {
    name: 'Groupe C',
    pct: 0.25,
    ideology_center: 0.4,
    loyalty: 0.8,
    candidate_affiliation: 'Carol',
  },
];

export interface IdentityVotingLabProps {
  candidates: Array<{ name: string; x: number; y: number }>;
  numVoters: number;
  seed: number;
}

const IdentityVotingPanel: React.FC<IdentityVotingLabProps> = ({ candidates, numVoters, seed }) => {
  const { t } = useTranslation();

  const sim = $api.useMutation('post', '/api/v2/theory/identity-voting');
  const data: IdentityData | null = (sim.data as IdentityData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('identity.error') : null;
  const [groups, setGroups] = useState<IdentityGroup[]>(DEFAULT_GROUPS);
  const [identityWeight, setIdentityWeight] = useState(0.5);
  const [crossPressure, setCrossPressure] = useState(true);
  const [activeView, setActiveView] = useState<'groups' | 'curve' | 'table'>('groups');

  // Each group's affiliation follows the Lab's candidates, cycling if there
  // are more groups than candidates.
  useEffect(() => {
    if (!candidates.length) return;
    setGroups((prev) =>
      prev.map((g, i) => ({
        ...g,
        candidate_affiliation: candidates[i % candidates.length].name,
      }))
    );
  }, [candidates]);

  const updateGroup = (i: number, field: keyof IdentityGroup, val: string | number) =>
    setGroups((prev) => prev.map((g, j) => (j === i ? { ...g, [field]: val } : g)));

  const run = useCallback(() => {
    sim.mutate({
      body: {
        candidates,
        num_voters: numVoters,
        seed,
        identity_groups: groups,
        identity_weight: identityWeight,
        cross_pressure: crossPressure,
        method: 'plurality',
      },
    });
  }, [candidates, numVoters, seed, groups, identityWeight, crossPressure, t, sim]);

  // ── Chart data ─────────────────────────────────────────────────────────────
  const groupsChartData =
    data?.group_results.map((gr, i) => ({
      name: gr.group_name,
      identity: Math.round(gr.group_vote_pct * 100),
      ideology: Math.round(gr.ideology_match * 100),
      color: GROUP_COLORS[i % GROUP_COLORS.length],
    })) ?? [];

  const curveData =
    data?.identity_weight_curve.map((pt) => ({
      weight: Math.round(pt.weight * 100),
      agreement: Math.round(pt.agreement_rate * 100),
      winner: pt.winner,
    })) ?? [];

  // Find weight where winner changes (first change from weight=0)
  let winnerChangeWeight: number | null = null;
  if (data) {
    const base = data.identity_weight_curve[0]?.winner;
    for (const pt of data.identity_weight_curve) {
      if (pt.winner !== base) {
        winnerChangeWeight = pt.weight;
        break;
      }
    }
  }

  const candNames = candidates.map((c) => c.name);

  return (
    <div>
      {/* ── Green quote ── */}
      <Alert
        variant="info"
        className="py-2 mb-3"
        data-testid="green-quote"
        style={{ fontSize: '0.78rem', borderLeft: '4px solid #0d6efd' }}
      >
        <strong>{t('identity.greenQuoteTitle')}</strong> {t('identity.greenQuote')}
      </Alert>

      {/* The candidates and the electorate come from the Lab's shared config. */}
      <div className="mb-2">
        <Badge variant="dark" style={{ fontSize: '0.68rem' }}>
          🔬 {t('lab.fromElectionLab')}
        </Badge>
      </div>

      {/* ── Group editor ── */}
      <div
        className="mb-3 border border-border rounded p-2"
        style={{ background: '#f8f9fa' }}
        data-testid="group-editor"
      >
        <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
          {t('identity.groupsTitle')}
        </div>
        {groups.map((g, i) => (
          <Row key={i} className="g-1 mb-1 items-center">
            <Col xs={3} md={2}>
              <Control
                size="sm"
                value={g.name}
                placeholder={t('identity.groupName')}
                data-testid={`group-name-${i}`}
                onChange={(e) => updateGroup(i, 'name', e.target.value)}
              />
            </Col>
            <Col xs={2} md={1} style={{ fontSize: '0.7rem' }}>
              <label className="mb-1 inline-block mb-0">{Math.round(g.pct * 100)}%</label>
              <Range
                min={5}
                max={80}
                step={5}
                value={Math.round(g.pct * 100)}
                data-testid={`group-pct-${i}`}
                onChange={(e) => updateGroup(i, 'pct', Number(e.target.value) / 100)}
              />
            </Col>
            <Col xs={2} md={2} style={{ fontSize: '0.7rem' }}>
              <label className="mb-1 inline-block mb-0">
                {t('identity.loyalty')} {Math.round(g.loyalty * 100)}%
              </label>
              <Range
                min={0}
                max={100}
                step={5}
                value={Math.round(g.loyalty * 100)}
                data-testid={`group-loyalty-${i}`}
                onChange={(e) => updateGroup(i, 'loyalty', Number(e.target.value) / 100)}
              />
            </Col>
            <Col xs={3} md={2}>
              <Select
                size="sm"
                value={g.candidate_affiliation}
                data-testid={`group-affil-${i}`}
                onChange={(e) => updateGroup(i, 'candidate_affiliation', e.target.value)}
              >
                {candNames.map((cn) => (
                  <option key={cn} value={cn}>
                    {cn}
                  </option>
                ))}
              </Select>
            </Col>
            <Col xs="auto">
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: GROUP_COLORS[i % GROUP_COLORS.length],
                  display: 'inline-block',
                }}
              />
            </Col>
          </Row>
        ))}
      </div>

      {/* ── Controls ── */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('identity.identityWeight')} — {Math.round(identityWeight * 100)}%
          </label>
          <Range
            min={0}
            max={100}
            step={5}
            value={Math.round(identityWeight * 100)}
            data-testid="identity-weight-slider"
            onChange={(e) => setIdentityWeight(Number(e.target.value) / 100)}
          />
        </Col>
        <Col xs="auto">
          <Check
            type="switch"
            id="cross-pressure"
            label={<span style={{ fontSize: '0.78rem' }}>{t('identity.crossPressure')}</span>}
            checked={crossPressure}
            data-testid="cross-pressure-toggle"
            onChange={(e) => setCrossPressure(e.target.checked)}
          />
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            size="sm"
            onClick={() => run()}
            disabled={loading}
            data-testid="run-btn"
          >
            {loading ? <Spinner size="sm" /> : t('identity.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="secondary" data-testid="prompt-alert">
          {t('identity.prompt')}
        </Alert>
      )}
      {error && (
        <Alert variant="danger" data-testid="error-alert">
          {error}
        </Alert>
      )}

      {data && (
        <>
          {/* ── Winner comparison ── */}
          <div className="flex gap-2 mb-3 flex-wrap" data-testid="winner-comparison">
            <WinnerBadge label={t('identity.sincereWinner')} winner={data.sincere_winner} />
            <div className="flex items-center text-muted-foreground" style={{ fontSize: '0.8rem' }}>
              →
            </div>
            <WinnerBadge
              label={t('identity.mixedWinner')}
              winner={data.mixed_winner}
              highlight={data.winner_changed}
            />
            <div className="flex items-center text-muted-foreground" style={{ fontSize: '0.8rem' }}>
              →
            </div>
            <WinnerBadge label={t('identity.identityWinner')} winner={data.identity_winner} />
            {data.winner_changed && (
              <Alert
                variant="warning"
                className="py-1 mb-0 ms-2"
                style={{ fontSize: '0.75rem' }}
                data-testid="winner-changed-alert"
              >
                ⚠️ {t('identity.winnerChanged')}
              </Alert>
            )}
          </div>

          {/* ── Cross-pressured stats ── */}
          <div
            className="flex gap-3 mb-3"
            style={{ fontSize: '0.78rem' }}
            data-testid="cross-pressured-stats"
          >
            <span>
              <Badge variant="secondary">{data.cross_pressured.count}</Badge>{' '}
              {t('identity.crossPressuredCount')}
            </span>
            <span>
              <Badge variant={data.cross_pressured.abstention_rate > 0.1 ? 'danger' : 'secondary'}>
                {Math.round(data.cross_pressured.abstention_rate * 100)}%
              </Badge>{' '}
              {t('identity.abstentionRate')}
            </span>
          </div>

          {/* ── View switcher ── */}
          <div className="flex gap-2 mb-3">
            {(['groups', 'curve', 'table'] as const).map((v) => (
              <Button
                key={v}
                size="sm"
                variant={activeView === v ? 'dark' : 'outline-secondary'}
                data-testid={`view-btn-${v}`}
                onClick={() => setActiveView(v)}
              >
                {t(`identity.view_${v}`)}
              </Button>
            ))}
          </div>

          {/* ── Groups view: loyalty vs ideology match ── */}
          {activeView === 'groups' && (
            <div data-testid="groups-view">
              <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('identity.groupsChartTitle')}
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={groupsChartData}
                  margin={{ top: 5, right: 20, bottom: 20, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                  <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
                  <Bar dataKey="identity" name={t('identity.identityVote')} radius={[3, 3, 0, 0]}>
                    {groupsChartData.map((pt, i) => (
                      <Cell key={i} fill={pt.color} />
                    ))}
                  </Bar>
                  <Bar
                    dataKey="ideology"
                    name={t('identity.ideologyVote')}
                    fill="#dee2e6"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Curve view: winner vs identity weight ── */}
          {activeView === 'curve' && (
            <div data-testid="curve-view">
              <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('identity.curveTitle')}
                {winnerChangeWeight !== null && (
                  <Badge variant="warning" className="ms-2" style={{ fontSize: '0.65rem' }}>
                    {t('identity.winnerChangesAt')} {Math.round(winnerChangeWeight * 100)}%
                  </Badge>
                )}
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={curveData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="weight"
                    unit="%"
                    tick={{ fontSize: 10 }}
                    label={{
                      value: t('identity.identityWeightLabel'),
                      position: 'insideBottom',
                      offset: -10,
                      fontSize: 10,
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    unit="%"
                    domain={[0, 100]}
                    label={{
                      value: t('identity.agreementRate'),
                      angle: -90,
                      position: 'insideLeft',
                      fontSize: 10,
                    }}
                  />
                  {winnerChangeWeight !== null && (
                    <ReferenceLine
                      x={Math.round(winnerChangeWeight * 100)}
                      stroke="#ffc107"
                      strokeWidth={2}
                      label={{
                        value: t('identity.winnerChanges'),
                        fontSize: 9,
                        fill: '#856404',
                        position: 'top',
                      }}
                    />
                  )}
                  <ReferenceLine
                    x={Math.round(identityWeight * 100)}
                    stroke="#0d6efd"
                    strokeDasharray="4 3"
                    label={{
                      value: t('identity.current'),
                      fontSize: 9,
                      fill: '#0d6efd',
                      position: 'top',
                    }}
                  />
                  <Tooltip formatter={numericTooltipFormatter((v: number) => `${v}%`)} />
                  <Line
                    type="monotone"
                    dataKey="agreement"
                    name={t('identity.agreementRate')}
                    stroke="#0d6efd"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
              <div className="text-muted-foreground mt-1" style={{ fontSize: '0.7rem' }}>
                {t('identity.curveDesc')}
              </div>
            </div>
          )}

          {/* ── Table view ── */}
          {activeView === 'table' && (
            <div data-testid="table-view">
              <table className="table table-sm table-bordered" style={{ fontSize: '0.73rem' }}>
                <thead className="table-light">
                  <tr>
                    <th>{t('identity.colGroup')}</th>
                    <th>{t('identity.colAffiliation')}</th>
                    <th>{t('identity.colSize')}</th>
                    <th>{t('identity.colLoyalty')}</th>
                    <th>{t('identity.colIdentityVote')}</th>
                    <th>{t('identity.colIdeologyMatch')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.group_results.map((gr, i) => (
                    <tr key={i} data-testid={`table-row-${i}`}>
                      <td>
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: GROUP_COLORS[i % GROUP_COLORS.length],
                            display: 'inline-block',
                            marginRight: 4,
                          }}
                        />
                        {gr.group_name}
                      </td>
                      <td>
                        <Badge variant="secondary" style={{ fontSize: '0.6rem' }}>
                          {gr.affiliation}
                        </Badge>
                      </td>
                      <td>{Math.round(gr.size_pct * 100)}%</td>
                      <td>
                        <div
                          style={{
                            width: Math.round(gr.loyalty * 60),
                            height: 6,
                            background: '#0d6efd',
                            borderRadius: 3,
                          }}
                        />
                        {Math.round(gr.loyalty * 100)}%
                      </td>
                      <td
                        style={{
                          fontWeight: 700,
                          color: gr.group_vote_pct > 0.7 ? '#198754' : undefined,
                        }}
                      >
                        {Math.round(gr.group_vote_pct * 100)}%
                      </td>
                      <td style={{ color: gr.ideology_match > 0.6 ? '#198754' : '#dc3545' }}>
                        {Math.round(gr.ideology_match * 100)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Real-world data ── */}
          <div
            className="mt-3 border border-border rounded p-3"
            data-testid="realworld-section"
            style={{ background: '#f8f9fa', fontSize: '0.75rem' }}
          >
            <div className="font-semibold mb-2">{t('identity.realworldTitle')}</div>
            <Row className="g-2">
              {(
                [
                  {
                    flag: '🇺🇸',
                    fact: '86% des Noirs américains ont voté Biden en 2020 — un vote stratégique de groupe protecteur, rationnel dans ce contexte.',
                  },
                  {
                    flag: '🇬🇧',
                    fact: "Brexit : l'identité Leaver/Remainer prédit mieux le vote 2019 que les positions économiques ou sociales.",
                  },
                  {
                    flag: '🇫🇷',
                    fact: "En France, le diplôme et la localisation (métropole vs périphérie) prédisent mieux le vote que l'idéologie déclarée.",
                  },
                  {
                    flag: '🇮🇳',
                    fact: "En Inde, la caste et la religion prédisent massivement le vote — l'idéologie individuelle est secondaire.",
                  },
                ] as const
              ).map(({ flag, fact }, i) => (
                <Col key={i} xs={12} md={6}>
                  <div className="border border-border rounded p-2" style={{ background: '#fff' }}>
                    <span className="me-1">{flag}</span>
                    <span className="text-muted-foreground">{fact}</span>
                  </div>
                </Col>
              ))}
            </Row>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert
            variant="secondary"
            className="mt-3"
            style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note"
          >
            <strong>{t('identity.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default IdentityVotingPanel;
