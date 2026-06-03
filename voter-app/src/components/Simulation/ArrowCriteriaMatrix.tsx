import React from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Table } from '@/components/ui/table';
import { ArrowCriteriaResult, MethodCriteria } from '../../types';
import MethodTooltip from '../shared/MethodTooltip';
import ResponsiveTable from '../shared/ResponsiveTable';
import { useTranslation } from 'react-i18next';

const CRITERIA_KEYS = [
  'condorcet_winner',
  'condorcet_loser',
  'monotonicity',
  'iia',
  'majority',
  'reversal_symmetry',
] as const;

// ── Helpers ────────────────────────────────────────────────────────────────

interface CellProps {
  value: boolean | null;
  violationRate?: number | null;
}

const CriterionCell: React.FC<CellProps> = ({ value, violationRate }) => {
  if (value === null) {
    return (
      <td className="text-center" style={{ backgroundColor: '#f8f9fa' }}>
        <span className="text-muted small">N/A</span>
      </td>
    );
  }

  const isSoftViolation =
    value === false && violationRate !== undefined && violationRate !== null && violationRate < 0.2;

  const bg = value ? '#d4edda' : isSoftViolation ? '#fff3cd' : '#f8d7da';
  const color = value ? '#155724' : isSoftViolation ? '#856404' : '#721c24';
  const symbol = value ? '✓' : isSoftViolation ? '~' : '✗';

  const tooltip =
    value === false && violationRate !== null && violationRate !== undefined
      ? `Taux de violation IIA : ${(violationRate * 100).toFixed(0)}%`
      : undefined;

  return (
    <td
      className="text-center fw-bold"
      style={{ backgroundColor: bg, color, fontSize: '1rem' }}
      title={tooltip}
    >
      {symbol}
      {tooltip && (
        <div style={{ fontSize: '0.65rem', fontWeight: 400, opacity: 0.85 }}>
          {(violationRate! * 100).toFixed(0)}%
        </div>
      )}
    </td>
  );
};

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  result: ArrowCriteriaResult;
}

const ArrowCriteriaMatrix: React.FC<Props> = ({ result }) => {
  const { t } = useTranslation();
  const { methods, summary } = result;
  const methodNames = Object.keys(methods);

  if (!methodNames.length) {
    return <Alert variant="info">{t('simulation.noData')}</Alert>;
  }

  const CRITERIA_LABELS: Record<string, string> = {
    condorcet_winner:  t('simulation.criteria.condorcetWinner'),
    condorcet_loser:   t('simulation.criteria.condorcetLoser'),
    monotonicity:      t('simulation.criteria.monotonicity'),
    iia:               t('simulation.criteria.iia'),
    majority:          t('simulation.criteria.majority'),
    reversal_symmetry: t('simulation.criteria.reversalSymmetry'),
  };

  const CRITERIA_DESCRIPTIONS: Record<string, string> = {
    condorcet_winner: t('simulation.criteriaDesc.condorcetWinner'),
    condorcet_loser: t('simulation.criteriaDesc.condorcetLoser'),
    monotonicity: t('simulation.criteriaDesc.monotonicity'),
    iia: t('simulation.criteriaDesc.iia'),
    majority: t('simulation.criteriaDesc.majority'),
    reversal_symmetry: t('simulation.criteriaDesc.reversalSymmetry'),
  };

  const scoreOf = (name: string) =>
    summary?.criteria_satisfaction_count?.[name] ?? 0;

  return (
    <div>
      <Alert variant="warning" className="py-2 mb-3">
        <strong>{t('simulation.arrowTheorem')}</strong> — {t('simulation.arrowExplanation')}
        {' '}{t('simulation.arrowEachMethod')}
      </Alert>

      <div className="d-flex gap-3 mb-3 flex-wrap">
        {[
          { bg: '#d4edda', color: '#155724', label: t('simulation.criteriaStatus.satisfied') },
          { bg: '#f8d7da', color: '#721c24', label: t('simulation.criteriaStatus.violated') },
          { bg: '#fff3cd', color: '#856404', label: t('simulation.criteriaStatus.softViolated') },
          { bg: '#f8f9fa', color: '#6c757d', label: t('simulation.criteriaStatus.notTestable') },
        ].map(({ bg, color, label }) => (
          <span key={label} className="d-flex align-items-center gap-1">
            <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: bg, border: `1px solid ${color}`, borderRadius: 2 }} />
            <small style={{ color }}>{label}</small>
          </span>
        ))}
        <small className="text-muted ms-2">{t('simulation.hoverIIA')}</small>
      </div>

      <ResponsiveTable>
        <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border text-center" style={{ minWidth: 600 }}>
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 140, textAlign: 'left' }}>{t('common.method')}</th>
              <th style={{ minWidth: 60 }}>{t('simulation.winner')}</th>
              {CRITERIA_KEYS.map((key) => (
                <th
                  key={key}
                  style={{ minWidth: 80, fontSize: '0.8rem', cursor: 'help' }}
                  title={CRITERIA_DESCRIPTIONS[key]}
                >
                  {CRITERIA_LABELS[key]}
                </th>
              ))}
              <th style={{ minWidth: 60 }}>Score</th>
            </tr>
          </thead>

          <tbody>
            {methodNames.map((method) => {
              const m: MethodCriteria = methods[method];
              const score = scoreOf(method);
              const isBest = method === summary?.most_criteria_satisfied;
              const isWorst = method === summary?.least_criteria_satisfied;

              return (
                <tr key={method} style={isBest ? { outline: '2px solid #198754' } : undefined}>
                  <td className="text-start ps-2 fw-semibold">
                    <MethodTooltip method={method} />
                    {isBest && (
                      <Badge variant="success" className="ms-2" style={{ fontSize: '0.65rem' }}>{t('simulation.better')}</Badge>
                    )}
                    {isWorst && !isBest && (
                      <Badge variant="danger" className="ms-2" style={{ fontSize: '0.65rem' }}>{t('simulation.worse')}</Badge>
                    )}
                  </td>
                  <td className="text-center">
                    <small className="text-muted">{m.winner ?? '—'}</small>
                  </td>
                  {CRITERIA_KEYS.map((key) => (
                    <CriterionCell
                      key={key}
                      value={m[key] as boolean | null}
                      violationRate={key === 'iia' ? m.iia_violation_rate : undefined}
                    />
                  ))}
                  <td
                    className="fw-bold text-center"
                    style={{
                      backgroundColor: score >= 5 ? '#d4edda' : score >= 3 ? '#fff3cd' : '#f8d7da',
                    }}
                  >
                    {score} / 6
                  </td>
                </tr>
              );
            })}
          </tbody>

          <tfoot>
            <tr className="table-light">
              <td colSpan={2} className="text-start ps-2 fw-semibold small">
                {t('simulation.criteriaSatisfied')}
              </td>
              {CRITERIA_KEYS.map((key) => {
                const satisfiedCount = methodNames.filter((m) => methods[m][key] === true).length;
                return (
                  <td key={key} className="text-center small text-muted">
                    {satisfiedCount}/{methodNames.length}
                  </td>
                );
              })}
              <td />
            </tr>
          </tfoot>
        </Table>
      </ResponsiveTable>

      {summary && (
        <div className="d-flex gap-3 mt-3 flex-wrap">
          <Alert variant="success" className="py-2 mb-0 flex-grow-1">
            <strong>{t('simulation.mostCriteria')}</strong>{' '}
            <MethodTooltip method={summary.most_criteria_satisfied} />
            {' '}({scoreOf(summary.most_criteria_satisfied)}/6)
          </Alert>
          <Alert variant="danger" className="py-2 mb-0 flex-grow-1">
            <strong>{t('simulation.leastCriteria')}</strong>{' '}
            <MethodTooltip method={summary.least_criteria_satisfied} />
            {' '}({scoreOf(summary.least_criteria_satisfied)}/6)
          </Alert>
        </div>
      )}

      <p className="text-muted small mt-3 mb-0">
        {t('simulation.criteriaNote')}
      </p>
    </div>
  );
};

export default ArrowCriteriaMatrix;
