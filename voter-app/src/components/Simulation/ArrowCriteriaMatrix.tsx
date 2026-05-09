import React from 'react';
import { Alert, Badge, Table } from 'react-bootstrap';
import { ArrowCriteriaResult, MethodCriteria } from '../../types';
import MethodTooltip from '../shared/MethodTooltip';

// ── Constants ──────────────────────────────────────────────────────────────

const CRITERIA_LABELS: Record<string, string> = {
  condorcet_winner:  'Vainqueur Condorcet',
  condorcet_loser:   'Perdant Condorcet',
  monotonicity:      'Monotonie',
  iia:               'IIA',
  majority:          'Majorité',
  reversal_symmetry: 'Symétrie inv.',
};

const CRITERIA_DESCRIPTIONS: Record<string, string> = {
  condorcet_winner:
    'Critère du vainqueur de Condorcet : si un candidat bat chacun des autres en duel direct, cette méthode doit l\'élire.',
  condorcet_loser:
    'Critère du perdant de Condorcet : un candidat qui perd chaque duel direct ne doit jamais être élu.',
  monotonicity:
    'Monotonie : classer un candidat plus haut dans certains bulletins (sans autre changement) ne doit pas le faire perdre.',
  iia:
    'Indépendance des alternatives non pertinentes (IIA) : supprimer un candidat non-vainqueur ne doit pas changer le vainqueur. Arrow démontre que l\'IIA est incompatible avec les autres critères.',
  majority:
    'Critère de majorité : si un candidat est classé premier par plus de 50% des électeurs, il doit gagner.',
  reversal_symmetry:
    'Symétrie de renversement : si toutes les préférences sont inversées (meilleur↔pire), le vainqueur original ne doit pas gagner l\'élection renversée.',
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
  const { methods, summary } = result;
  const methodNames = Object.keys(methods);

  if (!methodNames.length) {
    return <Alert variant="info">Aucune donnée disponible.</Alert>;
  }

  const scoreOf = (name: string) =>
    summary?.criteria_satisfaction_count?.[name] ?? 0;

  return (
    <div>
      <Alert variant="warning" className="py-2 mb-3">
        <strong>Théorème d'impossibilité d'Arrow (1951)</strong> — Aucune méthode de vote classée
        ne peut satisfaire simultanément tous ces critères avec 3 candidats ou plus.
        Chaque méthode ci-dessous en viole au moins un.
      </Alert>

      <div className="d-flex gap-3 mb-3 flex-wrap">
        {[
          { bg: '#d4edda', color: '#155724', label: '✓ Satisfait' },
          { bg: '#f8d7da', color: '#721c24', label: '✗ Violé' },
          { bg: '#fff3cd', color: '#856404', label: '~ Violé (taux < 20%)' },
          { bg: '#f8f9fa', color: '#6c757d', label: 'N/A (non testable)' },
        ].map(({ bg, color, label }) => (
          <span key={label} className="d-flex align-items-center gap-1">
            <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: bg, border: `1px solid ${color}`, borderRadius: 2 }} />
            <small style={{ color }}>{label}</small>
          </span>
        ))}
        <small className="text-muted ms-2">Survolez les cellules IIA pour voir le taux de violation.</small>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <Table bordered size="sm" className="text-center" style={{ minWidth: 600 }}>
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 140, textAlign: 'left' }}>Méthode</th>
              <th style={{ minWidth: 60 }}>Vainqueur</th>
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
                      <Badge bg="success" className="ms-2" style={{ fontSize: '0.65rem' }}>mieux</Badge>
                    )}
                    {isWorst && !isBest && (
                      <Badge bg="danger" className="ms-2" style={{ fontSize: '0.65rem' }}>moins bien</Badge>
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
                Critères satisfaits
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
      </div>

      {summary && (
        <div className="d-flex gap-3 mt-3 flex-wrap">
          <Alert variant="success" className="py-2 mb-0 flex-grow-1">
            <strong>Plus de critères satisfaits :</strong>{' '}
            <MethodTooltip method={summary.most_criteria_satisfied} />
            {' '}({scoreOf(summary.most_criteria_satisfied)}/6)
          </Alert>
          <Alert variant="danger" className="py-2 mb-0 flex-grow-1">
            <strong>Moins de critères satisfaits :</strong>{' '}
            <MethodTooltip method={summary.least_criteria_satisfied} />
            {' '}({scoreOf(summary.least_criteria_satisfied)}/6)
          </Alert>
        </div>
      )}

      <p className="text-muted small mt-3 mb-0">
        Résultats empiriques — chaque critère est vérifié sur la population simulée, pas démontré formellement.
        N/A signifie que le critère ne pouvait pas être testé sur cette population.
        L'IIA est testée en supprimant chaque candidat non-vainqueur et en vérifiant si le vainqueur change.
      </p>
    </div>
  );
};

export default ArrowCriteriaMatrix;
