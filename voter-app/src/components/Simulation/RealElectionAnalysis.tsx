import React from 'react';
import { Alert, Badge, Card, Col, Row, Table } from 'react-bootstrap';
import { RealElectionResult } from '../../types';

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
