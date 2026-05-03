import React from 'react';
import { Alert, Badge, Table } from 'react-bootstrap';
import { ArrowCriteriaResult, MethodCriteria } from '../../types';

// ── Constants ──────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  plurality:        'Plurality',
  two_round:        'Two-Round',
  borda:            'Borda',
  approval:         'Approval',
  irv:              'IRV',
  coombs:           "Coombs'",
  bucklin:          'Bucklin',
  minimax:          'Minimax',
  schulze:          'Schulze',
  kemeny_young:     'Kemeny-Young',
  condorcet:        'Condorcet',
  positional_score: 'Positional Score',
};

const CRITERIA_LABELS: Record<string, string> = {
  condorcet_winner:  'Condorcet Winner',
  condorcet_loser:   'Condorcet Loser',
  monotonicity:      'Monotonicity',
  iia:               'IIA',
  majority:          'Majority',
  reversal_symmetry: 'Reversal Sym.',
};

const CRITERIA_DESCRIPTIONS: Record<string, string> = {
  condorcet_winner:
    'Condorcet Winner Criterion: if a candidate beats every other candidate ' +
    'in pairwise duels, that candidate must win.',
  condorcet_loser:
    'Condorcet Loser Criterion: a candidate who loses every pairwise duel ' +
    'must never be elected.',
  monotonicity:
    'Monotonicity: ranking a candidate higher in some ballots (without ' +
    'changing other ballots) cannot cause that candidate to lose.',
  iia:
    'Independence of Irrelevant Alternatives (IIA): removing a non-winning ' +
    "candidate should not change the winner. Arrow's theorem proves this is " +
    'incompatible with the other criteria in ranked methods.',
  majority:
    'Majority Criterion: if a candidate is ranked first by more than 50% ' +
    'of voters, that candidate must win.',
  reversal_symmetry:
    'Reversal Symmetry: if all voter preferences are reversed (best↔worst), ' +
    'the original winner should not win the reversed election.',
};

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

  // Orange "~" for soft violations: IIA violated but at a low rate (< 20%)
  const isSoftViolation =
    value === false && violationRate !== undefined && violationRate !== null && violationRate < 0.2;

  const bg = value ? '#d4edda' : isSoftViolation ? '#fff3cd' : '#f8d7da';
  const color = value ? '#155724' : isSoftViolation ? '#856404' : '#721c24';
  const symbol = value ? '✓' : isSoftViolation ? '~' : '✗';

  const tooltip =
    value === false && violationRate !== null && violationRate !== undefined
      ? `IIA violation rate: ${(violationRate * 100).toFixed(0)}%`
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
  const { methods, summary } = result;
  const methodNames = Object.keys(methods);

  if (!methodNames.length) {
    return <Alert variant="info">No data available.</Alert>;
  }

  const scoreOf = (name: string) =>
    summary?.criteria_satisfaction_count?.[name] ?? 0;

  return (
    <div>
      {/* Arrow's theorem reminder */}
      <Alert variant="warning" className="py-2 mb-3">
        <strong>Arrow's Impossibility Theorem (1951)</strong> — No ranked voting
        rule can simultaneously satisfy all of these criteria when there are 3 or
        more candidates. Every method below violates at least one.
      </Alert>

      {/* Reading guide */}
      <div className="d-flex gap-3 mb-3 flex-wrap">
        {[
          { bg: '#d4edda', color: '#155724', label: '✓ Satisfied' },
          { bg: '#f8d7da', color: '#721c24', label: '✗ Violated' },
          {
            bg: '#fff3cd',
            color: '#856404',
            label: '~ Violated (rate < 20%)',
          },
          { bg: '#f8f9fa', color: '#6c757d', label: 'N/A (not testable)' },
        ].map(({ bg, color, label }) => (
          <span key={label} className="d-flex align-items-center gap-1">
            <span
              style={{
                display: 'inline-block',
                width: 16,
                height: 16,
                backgroundColor: bg,
                border: `1px solid ${color}`,
                borderRadius: 2,
              }}
            />
            <small style={{ color }}>{label}</small>
          </span>
        ))}
        <small className="text-muted ms-2">
          Hover IIA cells to see the violation rate.
        </small>
      </div>

      {/* Matrix table */}
      <div style={{ overflowX: 'auto' }}>
        <Table bordered size="sm" className="text-center" style={{ minWidth: 600 }}>
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 140, textAlign: 'left' }}>Method</th>
              <th style={{ minWidth: 60 }}>Winner</th>
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
                <tr
                  key={method}
                  style={isBest ? { outline: '2px solid #198754' } : undefined}
                >
                  <td className="text-start ps-2 fw-semibold">
                    {METHOD_LABELS[method] || method}
                    {isBest && (
                      <Badge bg="success" className="ms-2" style={{ fontSize: '0.65rem' }}>
                        best
                      </Badge>
                    )}
                    {isWorst && !isBest && (
                      <Badge bg="danger" className="ms-2" style={{ fontSize: '0.65rem' }}>
                        worst
                      </Badge>
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

          {/* Score row */}
          <tfoot>
            <tr className="table-light">
              <td colSpan={2} className="text-start ps-2 fw-semibold small">
                Criteria satisfied
              </td>
              {CRITERIA_KEYS.map((key) => {
                const satisfiedCount = methodNames.filter(
                  (m) => methods[m][key] === true
                ).length;
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
      </div>

      {/* Summary */}
      {summary && (
        <div className="d-flex gap-3 mt-3 flex-wrap">
          <Alert variant="success" className="py-2 mb-0 flex-grow-1">
            <strong>Most criteria:</strong>{' '}
            {METHOD_LABELS[summary.most_criteria_satisfied] || summary.most_criteria_satisfied}
            {' '}({scoreOf(summary.most_criteria_satisfied)}/6)
          </Alert>
          <Alert variant="danger" className="py-2 mb-0 flex-grow-1">
            <strong>Fewest criteria:</strong>{' '}
            {METHOD_LABELS[summary.least_criteria_satisfied] || summary.least_criteria_satisfied}
            {' '}({scoreOf(summary.least_criteria_satisfied)}/6)
          </Alert>
        </div>
      )}

      <p className="text-muted small mt-3 mb-0">
        Results are empirical — each criterion is verified on the simulated population,
        not formally proved. N/A means the criterion could not be tested with this
        population (e.g. monotonicity when no voter ranks the winner 2nd).
        IIA is tested by removing each non-winning candidate and checking if the winner
        changes; the violation rate is the proportion of removals that caused a change.
      </p>
    </div>
  );
};

export default ArrowCriteriaMatrix;
