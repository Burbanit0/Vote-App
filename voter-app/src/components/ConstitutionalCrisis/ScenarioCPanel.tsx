import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Trans, useTranslation } from 'react-i18next';
import { ConstitutionalResult } from '../../services/simulationCompareApi';

const COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

interface Props {
  result: ConstitutionalResult | null;
  loading: boolean;
  onRun: (numSeats: number) => void;
}

const ScenarioCPanel: React.FC<Props> = ({ result, loading, onRun }) => {
  const { t } = useTranslation();
  const [numSeats, setNumSeats] = useState(100);

  const multi = result?.multiwinner as Record<string, any> | undefined;
  const partyVotes = result?.party_votes ?? {};
  const parties = Object.keys(partyVotes);
  const colorMap = Object.fromEntries(parties.map((p, i) => [p, COLORS[i % COLORS.length]]));
  const totalVotes = Object.values(partyVotes).reduce((a, b) => a + b, 0);

  const METHOD_LABELS_MULTI: Record<string, string> = {
    dhondt: t('crisis.method.dhondt'),
    sainte_lague: t('crisis.method.sainte_lague'),
    largest_remainder_hare: t('crisis.method.largest_remainder_hare'),
  };

  // Stacked bar chart data: one entry per proportional method
  const chartData = Object.entries(METHOD_LABELS_MULTI).map(([key, label]) => {
    const seats = multi?.[key]?.seats ?? {};
    const gallagher = multi?.[key]?.metrics?.gallagher_index;
    return {
      method: label,
      gallagher,
      ...seats,
    };
  });

  return (
    <div>
      <p className="text-muted small mb-3">
        {t('crisis.scenarioCDesc')}
      </p>

      <Row className="g-3 mb-4">
        <Col md={5}>
          <Card>
            <CardBody>
              <label className="mb-1 inline-block">
                <Trans i18nKey="crisis.scenarioCSeats" values={{ n: numSeats }} />
              </label>
              <Range min={10} max={500} step={10} value={numSeats} onChange={(e) => setNumSeats(Number(e.target.value))} />
              <div className="d-flex justify-content-between">
                <small className="text-muted">10</small><small className="text-muted">500</small>
              </div>
            </CardBody>
          </Card>
        </Col>
        <Col md={7}>
          <Card>
            <CardBody>
              <small className="fw-semibold text-muted d-block mb-2">{t('crisis.scenarioCVoteDist')}</small>
              <div className="d-flex flex-wrap gap-2">
                {parties.map((p) => (
                  <span key={p} className="d-flex align-items-center gap-1">
                    <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: colorMap[p], display: 'inline-block' }} />
                    <small>{p} — {Math.round(partyVotes[p] / totalVotes * 100)}%</small>
                  </span>
                ))}
              </div>
            </CardBody>
          </Card>
        </Col>
      </Row>

      <div className="mb-4">
        <Button variant="success" onClick={() => onRun(numSeats)} disabled={loading}>
          {loading ? <><Spinner size="sm" className="me-2" />{t('crisis.simulating')}</> : t('crisis.runAssembly')}
        </Button>
      </div>

      {multi && (
        <>
          {/* Stacked bar chart */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2"><strong>{t('crisis.seatDistribution')}</strong></CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, numSeats]} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="method" tick={{ fontSize: 11 }} width={80} />
                  <Tooltip formatter={(v: number) => `${v} ${t('crisis.seats')}`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {parties.map((p) => (
                    <Bar key={p} dataKey={p} stackId="a" fill={colorMap[p]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Detail table */}
          <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-3">
            <thead className="table-light">
              <tr>
                <th>{t('common.method')}</th>
                {parties.map((p) => (
                  <th key={p} className="text-center">
                    <span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: colorMap[p], borderRadius: 2, marginRight: 4 }} />
                    {p}
                  </th>
                ))}
                <th className="text-center">{t('crisis.gallagher')}</th>
                <th className="text-center">{t('crisis.mostProportional')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(METHOD_LABELS_MULTI).map(([key, label]) => {
                const seats = multi[key]?.seats ?? {};
                const gallagher = multi[key]?.metrics?.gallagher_index;
                const isBest = multi.comparison?.most_proportional === key;
                return (
                  <tr key={key} style={isBest ? { backgroundColor: '#e8f4e8' } : undefined}>
                    <td className="fw-semibold ps-2">{label}</td>
                    {parties.map((p) => (
                      <td key={p} className="text-center">{seats[p] ?? 0}</td>
                    ))}
                    <td className="text-center">
                      {gallagher != null ? <Badge variant={gallagher < 0.05 ? 'success' : gallagher < 0.1 ? 'warning' : 'danger'}>{gallagher.toFixed(3)}</Badge> : '—'}
                    </td>
                    <td className="text-center">{isBest ? <span style={{ color: '#198754' }}>✓</span> : ''}</td>
                  </tr>
                );
              })}
              {/* Uninominal comparison */}
              {result?.uninominal_winner && (
                <tr style={{ backgroundColor: '#fff8e1' }}>
                  <td className="fw-semibold ps-2 text-warning-emphasis">{t('methods.plurality.label')}</td>
                  {parties.map((p) => (
                    <td key={p} className="text-center text-muted">
                      {p === result.uninominal_winner ? numSeats : 0}
                    </td>
                  ))}
                  <td className="text-center">
                    <Badge variant="danger">{t('crisis.veryHigh')}</Badge>
                  </td>
                  <td className="text-center"><span className="text-danger">{t('crisis.spoilerEffect')}</span></td>
                </tr>
              )}
            </tbody>
          </Table>
          <small className="text-muted d-block mb-3">
            {t('crisis.gallagherFootnote')}
          </small>

          <Card className="border-0" style={{ backgroundColor: '#f8f9fa' }}>
            <CardBody>
              <small className="fw-semibold">{t('crisis.analysis')}</small>
              <p className="mb-0 mt-1 text-muted" style={{ fontSize: '0.85rem' }}>{result?.conclusion}</p>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
};

export default ScenarioCPanel;
