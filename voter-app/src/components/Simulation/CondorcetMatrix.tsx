import React from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Table } from '@/components/ui/table';
import { CondorcetMatrixResult } from '../../types';

interface Props {
  result: CondorcetMatrixResult;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function cellStyle(winner: string, rowCandidate: string): React.CSSProperties {
  if (winner === rowCandidate) {
    return { backgroundColor: '#d4edda', color: '#155724', fontWeight: 600 };
  }
  if (winner === 'tie') {
    return { backgroundColor: '#f8f9fa', color: '#6c757d' };
  }
  return { backgroundColor: '#f8d7da', color: '#721c24' };
}

// ── Component ──────────────────────────────────────────────────────────────

const CondorcetMatrix: React.FC<Props> = ({ result }) => {
  const { candidates, matrix, condorcet_winner, condorcet_cycles } = result;

  if (!candidates.length) {
    return <Alert variant="info">No data available.</Alert>;
  }

  return (
    <div>
      {/* ── Duel table ── */}
      <div style={{ overflowX: 'auto' }}>
        <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border text-center" style={{ minWidth: 400 }}>
          <thead className="table-light">
            <tr>
              {/* Top-left corner label */}
              <th
                style={{
                  backgroundColor: '#f8f9fa',
                  fontSize: '0.75rem',
                  color: '#6c757d',
                  verticalAlign: 'middle',
                  minWidth: 110,
                }}
              >
                <span style={{ float: 'right' }}>↓ vs →</span>
              </th>
              {candidates.map((col) => (
                <th key={col} style={{ minWidth: 90, verticalAlign: 'middle' }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {candidates.map((rowCandidate) => (
              <tr key={rowCandidate}>
                <td className="fw-semibold text-start ps-2">{rowCandidate}</td>
                {candidates.map((colCandidate) => {
                  if (rowCandidate === colCandidate) {
                    return (
                      <td
                        key={colCandidate}
                        style={{ backgroundColor: '#e9ecef', color: '#adb5bd' }}
                      >
                        —
                      </td>
                    );
                  }
                  const duel = matrix[rowCandidate]?.[colCandidate];
                  if (!duel) return <td key={colCandidate}>?</td>;
                  return (
                    <td key={colCandidate} style={cellStyle(duel.winner, rowCandidate)}>
                      {(duel.pct_a * 100).toFixed(1)}%
                      <div style={{ fontSize: '0.7rem', opacity: 0.75 }}>
                        vs {(duel.pct_b * 100).toFixed(1)}%
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </Table>
      </div>

      {/* ── Reading guide ── */}
      <div className="d-flex gap-3 mb-3 flex-wrap">
        {[
          { color: '#d4edda', border: '#c3e6cb', label: 'Row candidate wins the duel' },
          { color: '#f8d7da', border: '#f5c6cb', label: 'Row candidate loses' },
          { color: '#f8f9fa', border: '#dee2e6', label: 'Tie' },
        ].map(({ color, border, label }) => (
          <span key={label} className="d-flex align-items-center gap-1">
            <span
              style={{
                display: 'inline-block',
                width: 14,
                height: 14,
                backgroundColor: color,
                border: `1px solid ${border}`,
                borderRadius: 2,
              }}
            />
            <small className="text-muted">{label}</small>
          </span>
        ))}
        <small className="text-muted ms-2">
          Each cell shows: % of voters who prefer the <em>row</em> candidate over the{' '}
          <em>column</em> candidate.
        </small>
      </div>

      {/* ── Condorcet winner or cycles ── */}
      {condorcet_winner ? (
        <Alert variant="success" className="mb-0 py-2">
          <strong>Condorcet winner: {condorcet_winner}</strong> — beats every other
          candidate in head-to-head duels.
        </Alert>
      ) : condorcet_cycles.length > 0 ? (
        <Alert variant="warning" className="mb-0 py-2">
          <strong>No Condorcet winner</strong> — cycle
          {condorcet_cycles.length > 1 ? 's' : ''} detected:
          <div className="mt-1 d-flex flex-wrap gap-2">
            {condorcet_cycles.map((cycle, i) => (
              <Badge key={i} variant="warning" className="fw-normal">
                {cycle[0]} &gt; {cycle[1]} &gt; {cycle[2]} &gt; {cycle[0]}
              </Badge>
            ))}
          </div>
        </Alert>
      ) : (
        <Alert variant="secondary" className="mb-0 py-2">
          No Condorcet winner and no cycles detected (possible tie at the top).
        </Alert>
      )}
    </div>
  );
};

export default CondorcetMatrix;
