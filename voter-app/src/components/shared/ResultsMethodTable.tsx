import React from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { Table } from '@/components/ui/table';
import MetricTooltip from './MetricTooltip';
import MethodInfo from '../playground/MethodInfo';
import type { ElectionResult } from '../../services/electionApi';

// ResultsMethodTable — the per-method winner / Bayesian-regret / Condorcet table.
// Extracted from ElectionLabPage so both the Lab and the playground's full-results
// module render the identical table (single source of truth).

const COLORS: Record<string, string> = {
  Green: '#007A33',
  Liberal: '#005CAB',
  Conservative: '#C8590A',
  Independent: '#6c757d',
};

const ResultsMethodTable: React.FC<{ result: ElectionResult }> = ({ result }) => {
  const { t } = useTranslation();
  const hasBlank = result.config.blank_vote?.enabled;
  const rows = Object.entries(result.methods).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div>
      {/* Summary badges */}
      <div className="flex gap-2 flex-wrap mb-3">
        <Badge variant="primary" className="inline-flex items-center gap-1">
          {t('electionLab.methodAgreement')}: {Math.round(result.inter_method_agreement * 100)}%
          <MetricTooltip metric="method_agreement" placement="bottom" />
        </Badge>
        {result.condorcet_winner && (
          <Badge variant="success">Condorcet: {result.condorcet_winner} ✓</Badge>
        )}
        {hasBlank && (
          <Badge variant="warning">
            {t('electionLab.blankRate')}: {Math.round(result.blank_rate * 100)}%
          </Badge>
        )}
      </div>

      <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border">
        <thead className="table-light">
          <tr>
            <th>{t('common.method')}</th>
            <th>{t('electionLab.winner')}</th>
            {hasBlank && <th>{t('electionLab.winnerWithBlank')}</th>}
            <th className="flex items-center gap-1">
              {t('simulation.bayesianRegret')}
              <MetricTooltip metric="bayesian_regret" placement="bottom" />
            </th>
            <th>
              Condorcet ✓
              <MetricTooltip metric="condorcet_compliance" placement="bottom" />
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([method, md]) => {
            const isCondorcet = result.condorcet_winner && md.winner === result.condorcet_winner;
            return (
              <tr key={method}>
                <td className="font-semibold" style={{ fontSize: '0.82rem' }}>
                  {method}
                  <MethodInfo
                    method={method}
                    context={{ condorcetExists: result.condorcet_winner != null }}
                  />
                </td>
                <td>
                  {md.winner ? (
                    <Badge
                      style={{
                        background:
                          COLORS[
                            result.candidates.find((c) => c.name === md.winner)?.party ?? ''
                          ] ?? '#666',
                      }}
                    >
                      {md.winner}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                  {isCondorcet && ' ✓'}
                </td>
                {hasBlank && (
                  <td>
                    {md.winner_with_blank ? (
                      <Badge variant={md.blank_triggered ? 'warning' : 'secondary'}>
                        {md.winner_with_blank}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                    {md.blank_triggered && <span className="text-[#cc9a00] ms-1">⚠</span>}
                  </td>
                )}
                <td style={{ fontSize: '0.8rem' }}>{md.bayesian_regret?.toFixed(4) ?? '—'}</td>
                <td className="text-center">
                  {md.condorcet_consistent === true && <span style={{ color: '#007A33' }}>✓</span>}
                  {md.condorcet_consistent === false && <span style={{ color: '#B71C1C' }}>✗</span>}
                  {md.condorcet_consistent === null && (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </div>
  );
};

export default ResultsMethodTable;
