import React from 'react';
import { Alert, Badge, Card, Col, Row, Table } from 'react-bootstrap';
import { RealElectionResult, BlankVoteAnalysis } from '../../types';

const METHOD_LABELS: Record<string, string> = {
  plurality:             'Plurality',
  two_round:             'Two-Round',
  borda:                 'Borda',
  approval:              'Approval',
  irv:                   'IRV',
  coombs:                "Coombs'",
  bucklin:               'Bucklin',
  minimax:               'Minimax',
  schulze:               'Schulze',
  condorcet:             'Condorcet',
  kemeny_young:          'Kemeny-Young',
  positional_score:      'Positional Score',
  simple_score:          'Simple Score',
  star_voting:           'STAR',
  median_voting:         'Median Score',
  mean_median_hybrid:    'Mean-Median',
  variance_based:        'Variance-Based',
};

interface Props {
  result: RealElectionResult;
}

// ── Blank vote section ─────────────────────────────────────────────────────

const KEY_METHODS_FOR_BLANK = ['plurality', 'irv', 'borda', 'schulze', 'approval'];
const KEY_METHOD_LABELS: Record<string, string> = {
  plurality: 'Pluralité', irv: 'IRV', borda: 'Borda',
  schulze: 'Schulze', approval: 'Approbation',
};

const BlankVoteSection: React.FC<{ analysis: BlankVoteAnalysis; methods: Record<string, string | null>; pluralityWinner: string }> = ({
  analysis, methods, pluralityWinner,
}) => {
  const blankPct = Math.round(analysis.estimated_blank_pct * 100 * 10) / 10;
  const crisisAny = analysis.competitive.triggered || analysis.threshold_30.triggered;

  return (
    <Card className={`mt-4 border-${crisisAny ? 'danger' : 'secondary'}`}>
      <Card.Header className={`d-flex align-items-center justify-content-between ${crisisAny ? 'bg-danger text-white' : ''}`}>
        <strong>⬜ Et avec le vote blanc reconnu ?</strong>
        <div className="d-flex align-items-center gap-2">
          <span style={{ fontSize: '0.9rem' }}>
            Taux historique de votes blancs/nuls : <strong>{blankPct}%</strong>
          </span>
          {crisisAny && (
            <Badge bg="warning" text="dark" style={{ fontSize: '0.8rem' }}>
              🚨 Crise constitutionnelle
            </Badge>
          )}
        </div>
      </Card.Header>
      <Card.Body>
        <p className="text-muted small mb-3">
          Si ces bulletins blancs/nuls avaient été comptabilisés comme un candidat "Vote Blanc", voici ce qui aurait changé selon deux règles constitutionnelles.
        </p>

        <div style={{ overflowX: 'auto' }}>
          <Table bordered size="sm">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 130 }}>Méthode</th>
                <th className="text-center" style={{ minWidth: 120 }}>
                  Sans vote blanc<br /><small className="text-muted fw-normal">(droit actuel)</small>
                </th>
                <th className="text-center" style={{ minWidth: 140 }}>
                  Règle compétitive<br /><small className="text-muted fw-normal">le blanc peut gagner</small>
                </th>
                <th className="text-center" style={{ minWidth: 160 }}>
                  Seuil 30%<br /><small className="text-muted fw-normal">{'>'} 30% → nouvelle élection</small>
                </th>
              </tr>
            </thead>
            <tbody>
              {KEY_METHODS_FOR_BLANK.map((method) => {
                const winner = methods[method] ?? null;
                const compWinner = analysis.competitive.winner;
                const thresh30Winner = analysis.threshold_30.winner;
                const compChanged = compWinner !== winner;
                const threshChanged = thresh30Winner !== winner;
                return (
                  <tr key={method}>
                    <td className="fw-semibold ps-2">{KEY_METHOD_LABELS[method] ?? method}</td>
                    <td className="text-center">
                      {winner ? <Badge bg="primary">{winner}</Badge> : <span className="text-muted">—</span>}
                    </td>
                    <td className="text-center" style={compChanged ? { backgroundColor: '#fff8e1' } : undefined}>
                      {analysis.competitive.triggered ? (
                        <Badge bg="warning" text="dark">⬜ Vote Blanc</Badge>
                      ) : winner ? (
                        <Badge bg="secondary">{winner}</Badge>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                      {compChanged && <span className="ms-1" style={{ color: '#dc3545', fontSize: '0.8rem' }}>✗</span>}
                    </td>
                    <td className="text-center" style={threshChanged ? { backgroundColor: '#fce8e8' } : undefined}>
                      {analysis.threshold_30.triggered ? (
                        <span style={{ color: '#dc3545', fontSize: '0.8rem' }}>Nouvelle élection requise</span>
                      ) : winner ? (
                        <Badge bg="secondary">{winner}</Badge>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>

        {/* Consequences */}
        <Row className="g-2 mt-2">
          <Col md={6}>
            <div className={`p-2 rounded border-start border-3 ${analysis.competitive.triggered ? 'border-danger' : 'border-success'}`}
                 style={{ backgroundColor: '#f8f9fa', fontSize: '0.82rem' }}>
              <strong>Règle compétitive :</strong> {analysis.competitive.consequence}
            </div>
          </Col>
          <Col md={6}>
            <div className={`p-2 rounded border-start border-3 ${analysis.threshold_30.triggered ? 'border-danger' : 'border-success'}`}
                 style={{ backgroundColor: '#f8f9fa', fontSize: '0.82rem' }}>
              <strong>Seuil 30% :</strong> {analysis.threshold_30.consequence}
            </div>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  );
};

// ── Main component ─────────────────────────────────────────────────────────

const RealElectionAnalysis: React.FC<Props> = ({ result }) => {
  const { election, plurality_winner, first_round_results, divergences, summary } = result;

  const nDifferent = summary.methods_with_different_winner;
  const nTotal     = summary.total_methods_with_winner;

  // Sort: divergences first, then alphabetical within each group
  const sorted = [...divergences].sort((a, b) => {
    if (a.differs_from_plurality !== b.differs_from_plurality)
      return a.differs_from_plurality ? -1 : 1;
    return (METHOD_LABELS[a.method] ?? a.method).localeCompare(
      METHOD_LABELS[b.method] ?? b.method
    );
  });

  // First-round bar widths (% of max for visual)
  const maxPct = Math.max(...Object.values(first_round_results));

  return (
    <div>
      {/* ── Election header ── */}
      <Card className="mb-4 border-0 bg-light">
        <Card.Body>
          <Row>
            <Col>
              <h5 className="mb-1">
                {election.name}
                <Badge bg="secondary" className="ms-2" style={{ fontSize: '0.75rem' }}>
                  {election.country} · {election.year}
                </Badge>
              </h5>
              <p className="text-muted small mb-2">{election.description}</p>
              <p className="text-muted" style={{ fontSize: '0.75rem' }}>
                Source: {election.source}
              </p>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* ── First-round results ── */}
      <Card className="mb-4">
        <Card.Header>
          <strong>First-Round Results</strong>
          <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
            — actual votes as used to generate synthetic rankings
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
                    <span
                      style={{
                        minWidth: 130,
                        fontWeight: isPlurality ? 700 : 400,
                        fontSize: '0.85rem',
                      }}
                    >
                      {candidate}
                      {isPlurality && (
                        <Badge bg="primary" className="ms-1" style={{ fontSize: '0.65rem' }}>
                          1st
                        </Badge>
                      )}
                    </span>
                    <div
                      style={{
                        flex: 1,
                        height: 14,
                        backgroundColor: '#e9ecef',
                        borderRadius: 3,
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${(pct / maxPct) * 100}%`,
                          backgroundColor: isPlurality ? '#0d6efd' : '#6ea8fe',
                          borderRadius: 3,
                          transition: 'width 0.3s',
                        }}
                      />
                    </div>
                    <span style={{ minWidth: 45, fontSize: '0.82rem', textAlign: 'right' }}>
                      {pct.toFixed(1)}%
                    </span>
                    <span
                      className="text-muted"
                      style={{ minWidth: 200, fontSize: '0.75rem' }}
                    >
                      {party}
                    </span>
                  </div>
                );
              })}
          </div>
        </Card.Body>
      </Card>

      {/* ── Summary banner ── */}
      {nDifferent > 0 ? (
        <Alert variant="warning" className="py-2 mb-4">
          <strong>
            {nDifferent} method{nDifferent > 1 ? 's' : ''} out of {nTotal} would have
            elected a different winner
          </strong>{' '}
          than the plurality result ({plurality_winner}).
          {nDifferent > nTotal / 2
            ? ' The majority of methods disagree with plurality — a strong signal of vote splitting.'
            : ''}
        </Alert>
      ) : (
        <Alert variant="success" className="py-2 mb-4">
          All methods agree: <strong>{plurality_winner}</strong> wins under every
          voting rule. No plurality paradox detected for this election.
        </Alert>
      )}

      {/* ── Methods comparison table ── */}
      <Card>
        <Card.Header>
          <strong>Method Comparison</strong>
          <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
            — divergences shown first
          </span>
        </Card.Header>
        <Card.Body className="p-0">
          <Table bordered size="sm" className="mb-0">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 160 }}>Voting method</th>
                <th className="text-center" style={{ minWidth: 130 }}>
                  Winner elected
                </th>
                <th className="text-center" style={{ minWidth: 90 }}>
                  vs. Plurality
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(({ method, winner, differs_from_plurality }) => {
                const rowStyle = differs_from_plurality
                  ? { backgroundColor: '#fff3cd' }
                  : undefined;
                return (
                  <tr key={method} style={rowStyle}>
                    <td className="ps-2 fw-semibold">
                      {METHOD_LABELS[method] ?? method}
                    </td>
                    <td className="text-center">
                      {winner ? (
                        <Badge
                          bg={
                            winner === plurality_winner
                              ? 'primary'
                              : differs_from_plurality
                              ? 'warning'
                              : 'secondary'
                          }
                          text={differs_from_plurality ? 'dark' : undefined}
                        >
                          {winner}
                        </Badge>
                      ) : (
                        <span className="text-muted small">No winner</span>
                      )}
                    </td>
                    <td className="text-center fw-bold" style={{ fontSize: '1.1rem' }}>
                      {winner === null ? (
                        <span className="text-muted">—</span>
                      ) : differs_from_plurality ? (
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
        </Card.Body>
      </Card>

      {result.blank_vote_analysis && (
        <BlankVoteSection
          analysis={result.blank_vote_analysis}
          methods={result.methods}
          pluralityWinner={plurality_winner}
        />
      )}

      <p className="text-muted small mt-3 mb-0">
        Rankings are synthetic — generated from real vote shares using an
        ideological proximity model. Each voter who chose candidate X ranks
        all other candidates in order of ideological distance from X.
        This is a simplified model; actual voter preferences are more complex.
      </p>
    </div>
  );
};

export default RealElectionAnalysis;
