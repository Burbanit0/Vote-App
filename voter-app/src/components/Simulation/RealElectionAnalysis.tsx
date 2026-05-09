import React from 'react';
import { Alert, Badge, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import MethodTooltip from '../shared/MethodTooltip';
import { RealElectionResult } from '../../types';

const METHOD_LABELS: Record<string, string> = {
  plurality:          'Pluralité',
  two_round:          'Deux tours',
  borda:              'Borda',
  approval:           'Approbation',
  irv:                'IRV',
  coombs:             "Coombs'",
  bucklin:            'Bucklin',
  minimax:            'Minimax',
  schulze:            'Schulze',
  condorcet:          'Condorcet',
  kemeny_young:       'Kemeny-Young',
  positional_score:   'Score positionnel',
  simple_score:       'Score simple',
  star_voting:        'STAR',
  median_voting:      'Score médian',
  mean_median_hybrid: 'Moy.-Médiane',
  variance_based:     'Variance',
};

interface Props {
  result: RealElectionResult;
  blankVoteEnabled: boolean;
  blankLoading: boolean;
  onToggleBlankVote: (enabled: boolean) => void;
}

// ── Blank vote comparison table ────────────────────────────────────────────

const BlankComparisonTable: React.FC<{
  methods: Record<string, string | null>;
  methodsWithBlank: Record<string, string | null>;
  pluralityWinner: string;
}> = ({ methods, methodsWithBlank, pluralityWinner }) => {
  const methodNames = Object.keys(methods);
  const crisisCount = methodNames.filter((m) => methodsWithBlank[m] === 'Blank').length;
  const changedCount = methodNames.filter((m) => methods[m] !== methodsWithBlank[m]).length;

  return (
    <div className="mt-3">
      {/* Summary badges */}
      <div className="d-flex gap-2 mb-3 flex-wrap align-items-center">
        {crisisCount > 0 && (
          <Badge bg="danger" style={{ fontSize: '0.82rem' }}>
            🚨 Crise constitutionnelle — {crisisCount} méthode{crisisCount > 1 ? 's' : ''} élit le Vote Blanc
          </Badge>
        )}
        {changedCount > 0 && (
          <Badge bg="warning" text="dark" style={{ fontSize: '0.82rem' }}>
            ⚠️ {changedCount}/{methodNames.length} méthodes changent de vainqueur
          </Badge>
        )}
        {changedCount === 0 && (
          <Badge bg="success" style={{ fontSize: '0.82rem' }}>
            ✓ Aucun changement de vainqueur — le vote blanc ne modifie pas l'issue
          </Badge>
        )}
      </div>

      {/* Comparison table */}
      <div style={{ overflowX: 'auto' }}>
        <Table bordered size="sm">
          <thead className="table-light">
            <tr>
              <th style={{ minWidth: 150 }}>Méthode</th>
              <th className="text-center" style={{ minWidth: 130 }}>
                Sans vote blanc<br /><small className="fw-normal text-muted">(résultat officiel)</small>
              </th>
              <th className="text-center" style={{ minWidth: 150 }}>
                Avec vote blanc reconnu<br /><small className="fw-normal text-muted">(simulation)</small>
              </th>
              <th className="text-center" style={{ minWidth: 100 }}>Changement ?</th>
            </tr>
          </thead>
          <tbody>
            {methodNames.map((method) => {
              const w1 = methods[method] ?? null;
              const w2 = methodsWithBlank[method] ?? null;
              const changed = w1 !== w2;
              const isCrisis = w2 === 'Blank';
              return (
                <tr
                  key={method}
                  style={
                    isCrisis
                      ? { backgroundColor: '#fce8e8' }
                      : changed
                      ? { backgroundColor: '#fff8e1' }
                      : undefined
                  }
                >
                  <td className="ps-2 fw-semibold"><MethodTooltip method={method} /></td>
                  <td className="text-center">
                    {w1 ? (
                      <Badge bg={w1 === pluralityWinner ? 'primary' : 'secondary'}>{w1}</Badge>
                    ) : (
                      <span className="text-muted small">—</span>
                    )}
                  </td>
                  <td className="text-center">
                    {isCrisis ? (
                      <Badge bg="danger">⬜ Vote Blanc</Badge>
                    ) : w2 ? (
                      <Badge bg={changed ? 'warning' : 'secondary'} text={changed ? 'dark' : undefined}>{w2}</Badge>
                    ) : (
                      <span className="text-muted small">—</span>
                    )}
                  </td>
                  <td className="text-center fw-bold" style={{ fontSize: '1rem' }}>
                    {isCrisis ? (
                      <span style={{ color: '#dc3545' }}>🚨</span>
                    ) : changed ? (
                      <span style={{ color: '#dc3545' }}>✗</span>
                    ) : (
                      <span style={{ color: '#198754' }}>✓</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>
      <small className="text-muted">
        🔴 Fond rouge = Vote Blanc élu (crise) · 🟡 Fond jaune = vainqueur modifié
      </small>
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────

const RealElectionAnalysis: React.FC<Props> = ({
  result,
  blankVoteEnabled,
  blankLoading,
  onToggleBlankVote,
}) => {
  const { election, plurality_winner, first_round_results, divergences, summary } = result;

  const nDifferent = summary.methods_with_different_winner;
  const nTotal     = summary.total_methods_with_winner;
  const blankPct   = election.estimated_blank_pct ?? 0;

  const sorted = [...divergences].sort((a, b) => {
    if (a.differs_from_plurality !== b.differs_from_plurality)
      return a.differs_from_plurality ? -1 : 1;
    return (METHOD_LABELS[a.method] ?? a.method).localeCompare(METHOD_LABELS[b.method] ?? b.method);
  });

  const maxPct = Math.max(...Object.values(first_round_results));

  return (
    <div>
      {/* ── Election header ── */}
      <Card className="mb-4 border-0 bg-light">
        <Card.Body>
          <h5 className="mb-1">
            {election.name}
            <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.75rem' }}>
              {election.country} · {election.year}
            </Badge>
          </h5>
          <p className="text-muted small mb-2">{election.description}</p>
          <p className="text-muted" style={{ fontSize: '0.75rem' }}>Source : {election.source}</p>
        </Card.Body>
      </Card>

      {/* ── First-round results ── */}
      <Card className="mb-4">
        <Card.Header>
          <strong>Résultats du premier tour</strong>
          <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
            — votes réels utilisés pour générer les bulletins synthétiques
          </span>
        </Card.Header>
        <Card.Body>
          <div className="d-flex flex-column gap-1">
            {Object.entries(first_round_results)
              .sort((a, b) => b[1] - a[1])
              .map(([candidate, pct]) => {
                const party = election.candidates.find((c) => c.name === candidate)?.party ?? '';
                const isPlurality = candidate === plurality_winner;
                return (
                  <div key={candidate} className="d-flex align-items-center gap-2">
                    <span style={{ minWidth: 150, fontWeight: isPlurality ? 700 : 400, fontSize: '0.85rem' }}>
                      {candidate}
                      {isPlurality && <Badge bg="primary" className="ms-1" style={{ fontSize: '0.65rem' }}>1er</Badge>}
                    </span>
                    <div style={{ flex: 1, height: 14, backgroundColor: '#e9ecef', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${(pct / maxPct) * 100}%`, backgroundColor: isPlurality ? '#0d6efd' : '#6ea8fe', borderRadius: 3 }} />
                    </div>
                    <span style={{ minWidth: 45, fontSize: '0.82rem', textAlign: 'right' }}>{pct.toFixed(1)}%</span>
                    <span className="text-muted" style={{ minWidth: 200, fontSize: '0.75rem' }}>{party}</span>
                  </div>
                );
              })}
          </div>
        </Card.Body>
      </Card>

      {/* ── Summary banner ── */}
      {nDifferent > 0 ? (
        <Alert variant="warning" className="py-2 mb-4">
          <strong>{nDifferent} méthode{nDifferent > 1 ? 's' : ''} sur {nTotal}</strong> auraient élu un vainqueur différent de la pluralité ({plurality_winner}).
          {nDifferent > nTotal / 2 ? ' La majorité des méthodes diverge — fort signal d\'effet spoiler.' : ''}
        </Alert>
      ) : (
        <Alert variant="success" className="py-2 mb-4">
          Toutes les méthodes s'accordent : <strong>{plurality_winner}</strong> gagne sous chaque règle de vote.
        </Alert>
      )}

      {/* ── Methods comparison table ── */}
      <Card className="mb-4">
        <Card.Header>
          <strong>Comparaison des méthodes</strong>
          <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>— divergences en premier</span>
        </Card.Header>
        <Card.Body className="p-0">
          <Table bordered size="sm" className="mb-0">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 160 }}>Méthode de vote</th>
                <th className="text-center" style={{ minWidth: 130 }}>Vainqueur élu</th>
                <th className="text-center" style={{ minWidth: 90 }}>vs. Pluralité</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(({ method, winner, differs_from_plurality }) => (
                <tr key={method} style={differs_from_plurality ? { backgroundColor: '#fff3cd' } : undefined}>
                  <td className="ps-2 fw-semibold"><MethodTooltip method={method} /></td>
                  <td className="text-center">
                    {winner ? (
                      <Badge bg={winner === plurality_winner ? 'primary' : differs_from_plurality ? 'warning' : 'secondary'} text={differs_from_plurality ? 'dark' : undefined}>
                        {winner}
                      </Badge>
                    ) : (
                      <span className="text-muted small">Aucun vainqueur</span>
                    )}
                  </td>
                  <td className="text-center fw-bold" style={{ fontSize: '1.1rem' }}>
                    {winner === null ? <span className="text-muted">—</span>
                      : differs_from_plurality ? <span style={{ color: '#dc3545' }}>✗</span>
                      : <span style={{ color: '#198754' }}>✓</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* ── Vote blanc simulation ── */}
      <Card className={blankVoteEnabled ? 'border-warning' : ''}>
        <Card.Header className="d-flex align-items-center justify-content-between">
          <div className="d-flex align-items-center gap-3">
            <strong>⬜ Simuler avec vote blanc reconnu</strong>
            {blankPct > 0 && (
              <span className="text-muted small">
                Taux historique : {Math.round(blankPct * 100 * 10) / 10}% des bulletins
              </span>
            )}
          </div>
          <div className="d-flex align-items-center gap-2">
            {blankLoading && <Spinner size="sm" className="text-warning" />}
            <Form.Switch
              id="blank-vote-toggle"
              checked={blankVoteEnabled}
              onChange={(e) => onToggleBlankVote(e.target.checked)}
              label={blankVoteEnabled ? 'Activé' : 'Désactivé'}
              disabled={blankLoading}
            />
          </div>
        </Card.Header>
        <Card.Body>
          {blankVoteEnabled && result.methods_with_blank ? (
            <BlankComparisonTable
              methods={result.methods}
              methodsWithBlank={result.methods_with_blank}
              pluralityWinner={plurality_winner}
            />
          ) : blankLoading ? (
            <div className="text-center py-3 text-muted">
              <Spinner size="sm" className="me-2" />
              Simulation du vote blanc en cours…
            </div>
          ) : (
            <p className="text-muted mb-0 small">
              Activez ce toggle pour relancer l'analyse en insérant le vote blanc comme candidat à part entière.
              Les {Math.round(blankPct * 100 * 10) / 10 || '?'}% d'électeurs ayant voté blanc en réalité
              le classeront en premier ; tous les autres le classeront en dernier.
            </p>
          )}
        </Card.Body>
      </Card>

      <p className="text-muted small mt-3 mb-0">
        Les bulletins sont synthétiques — générés depuis les scores réels via un modèle de proximité idéologique.
        Chaque électeur ayant voté X classe les autres candidats par distance idéologique croissante à X.
      </p>
    </div>
  );
};

export default RealElectionAnalysis;
