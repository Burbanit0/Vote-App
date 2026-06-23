/**
 * NOTAPanel — simulates "None Of The Above" as an official ballot option.
 * Voters cast NOTA if their best candidate's utility falls below the threshold.
 * Three constitutional rules: invalidate, force runoff, or seat NOTA (Nevada).
 */
import React, { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { $api } from '../../api/hooks';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface NotePoint {
  threshold: number;
  nota_pct: number;
  nota_wins: boolean;
  winner: string | null;
}

interface MethodEntry {
  winner: string | null;
  nota_pct: number;
  election_valid: boolean;
}

interface NotaData {
  nota_pct: number;
  election_valid: boolean;
  winner: string | null;
  nota_curve: NotePoint[];
  method_comparison: Record<string, MethodEntry>;
  pedagogical_note: string;
  nota_rule: string;
  nota_threshold: number;
}

// ── Tipping point helper ──────────────────────────────────────────────────────

function findTippingPoint(curve: NotePoint[]): number | null {
  for (const pt of curve) {
    if (pt.nota_pct >= 0.5) return pt.threshold;
  }
  return null;
}

// ── Rule badge ────────────────────────────────────────────────────────────────

interface RuleBadgeProps {
  data: NotaData;
  t: (k: string) => string;
}

const RuleBadge: React.FC<RuleBadgeProps> = ({ data, t }) => {
  if (!data.election_valid) {
    return (
      <Alert
        variant="danger"
        data-testid="election-invalid-alert"
        className="inline-block py-1 px-2 mb-0"
      >
        {data.nota_rule === 'invalidate' ? t('nota.invalidated') : t('nota.runoffRequired')}
      </Alert>
    );
  }
  if (data.winner === 'NOTA') {
    return (
      <Alert
        variant="warning"
        data-testid="nota-elected-alert"
        className="inline-block py-1 px-2 mb-0"
      >
        {t('nota.notaElected')}
      </Alert>
    );
  }
  return (
    <Badge variant="success" data-testid="election-valid-badge" style={{ fontSize: '0.8rem' }}>
      {t('nota.electionValid')}: {data.winner}
    </Badge>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const NOTAPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [threshold, setThreshold] = useState(0.3);
  const [notaRule, setNotaRule] = useState('invalidate');
  const sim = $api.useMutation('post', '/api/v2/election/nota');
  const data: NotaData | null = (sim.data as NotaData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('nota.error') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (thr: number, rule: string) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          nota_threshold: thr,
          nota_rule: rule,
          method: 'plurality',
        },
      });
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(threshold, notaRule);

  const handleThresholdChange = (v: number) => {
    setThreshold(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(v, notaRule), DEBOUNCE_MS);
  };

  const tippingPoint = data ? findTippingPoint(data.nota_curve) : null;
  const methods = data ? Object.keys(data.method_comparison) : [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={5}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('nota.thresholdLabel')}: <strong>{threshold.toFixed(2)}</strong>
          </label>
          <Range
            data-testid="nota-threshold-slider"
            min={0}
            max={1}
            step={0.01}
            value={threshold}
            onChange={(e) => handleThresholdChange(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">{t('nota.ruleLabel')}</label>
          <Select
            size="sm"
            value={notaRule}
            data-testid="nota-rule-select"
            onChange={(e) => setNotaRule(e.target.value)}
          >
            <option value="invalidate">{t('nota.invalidate')}</option>
            <option value="runoff">{t('nota.runoff')}</option>
            <option value="winner_take_all">{t('nota.winner_take_all')}</option>
          </Select>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}>
            {loading ? <Spinner size="sm" /> : t('nota.run')}
          </Button>
        </Col>
        {data && (
          <Col xs="auto">
            <PinToCentralButton
              type="nota"
              icon="🚫"
              label={`${t('nota.run')} — ${Math.round(threshold * 100)}%`}
              summary={
                data.winner === 'NOTA'
                  ? `${t('nota.runoffRequired')}`
                  : `${t('nota.electionValid')}: ${data.winner ?? '—'}`
              }
              methodsChanged={data.winner === 'NOTA' ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {/* Rule explanations */}
      <div className="flex gap-2 flex-wrap mb-3" style={{ fontSize: '0.75rem', color: '#6c757d' }}>
        <span>
          🇮🇳 {t('nota.invalidate')}: {t('nota.invalidateDesc')}
        </span>
        <span>
          🔄 {t('nota.runoff')}: {t('nota.runoffDesc')}
        </span>
        <span>
          🇺🇸 {t('nota.winner_take_all')}: {t('nota.winner_take_allDesc')}
        </span>
      </div>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('nota.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="flex flex-wrap gap-2 items-center mb-3">
            <Badge
              variant={
                data.nota_pct > 0.5 ? 'danger' : data.nota_pct > 0.25 ? 'warning' : 'secondary'
              }
              data-testid="nota-pct-badge"
              style={{ fontSize: '0.8rem' }}
            >
              NOTA: {Math.round(data.nota_pct * 100)}%
            </Badge>
            <RuleBadge data={data} t={t} />
            {tippingPoint != null && (
              <Badge variant="info" data-testid="tipping-point-badge">
                {t('nota.tippingPoint')} {tippingPoint.toFixed(2)}
              </Badge>
            )}
          </div>

          {/* Nota curve */}
          <div data-testid="nota-curve-chart" className="mb-4">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('nota.curveTitle')}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.nota_curve} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="threshold"
                  tickFormatter={(v: number) => v.toFixed(2)}
                  label={{
                    value: t('nota.thresholdLabel'),
                    position: 'insideBottom',
                    offset: -2,
                    fontSize: 10,
                  }}
                />
                <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Legend />
                {/* 50% line */}
                <ReferenceLine
                  y={0.5}
                  stroke="#dc3545"
                  strokeDasharray="4 2"
                  label={{ value: '50%', fill: '#dc3545', fontSize: 10 }}
                />
                {/* Current threshold */}
                <ReferenceLine x={threshold} stroke="#6c757d" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="nota_pct"
                  name={t('nota.notaPct')}
                  stroke="#dc3545"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
            {tippingPoint != null && (
              <div className="text-[#dc3545] mt-1" style={{ fontSize: '0.78rem' }}>
                ⚠ {t('nota.notaWinsAt')} {tippingPoint.toFixed(2)}
              </div>
            )}
          </div>

          {/* Method comparison table */}
          <div className="font-semibold mb-2" style={{ fontSize: '0.85rem' }}>
            {t('nota.methodTableTitle')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50"
            data-testid="method-comparison-table"
          >
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('nota.method')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('nota.notaPct')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('nota.winner')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('nota.valid')}</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((meth) => {
                const e = data.method_comparison[meth];
                const isLowest =
                  e.nota_pct ===
                  Math.min(...methods.map((m) => data.method_comparison[m].nota_pct));
                return (
                  <tr
                    key={meth}
                    style={{ background: isLowest ? '#f0fff4' : undefined }}
                    data-testid={`method-row-${meth}`}
                  >
                    <td style={{ fontSize: '0.78rem' }}>
                      <code>{meth}</code>
                      {isLowest && (
                        <Badge variant="success" className="ms-1" style={{ fontSize: '0.6rem' }}>
                          {t('nota.mostInclusive')}
                        </Badge>
                      )}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      <span style={{ color: e.nota_pct > 0.5 ? '#dc3545' : '#6c757d' }}>
                        {Math.round(e.nota_pct * 100)}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>{e.winner ?? '—'}</td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {e.election_valid ? (
                        <span style={{ color: '#198754' }}>✓</span>
                      ) : (
                        <span style={{ color: '#dc3545' }}>✗</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('nota.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default NOTAPanel;
