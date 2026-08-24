import React from 'react';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Table } from '@/components/ui/table';

interface PairwiseMatrixCardProps {
  /** Card header text, e.g. "Pairwise Opposition Matrix". */
  title: string;
  candidates: string[];
  /** Off-diagonal cell content. The diagonal always renders '-' — a candidate
   * never faces itself, so every Condorcet-family table agrees on that. */
  cellContent: (c1: string, c2: string, i: number, j: number) => React.ReactNode;
}

/**
 * Shared head-to-head table for the Condorcet-family visualisations
 * (Minimax, Schulze, Kemeny-Young). Only the cell content differs between
 * them — the row/column headers, diagonal, and table chrome are identical.
 */
const PairwiseMatrixCard: React.FC<PairwiseMatrixCardProps> = ({
  title,
  candidates,
  cellContent,
}) => (
  <Card className="mt-3">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2">{title}</CardHeader>
    <CardBody>
      <div className="table-responsive">
        <Table className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50">
          <thead>
            <tr>
              <th></th>
              {candidates.map((candidate) => (
                <th key={candidate}>{candidate}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {candidates.map((c1, i) => (
              <tr key={c1}>
                <th>{c1}</th>
                {candidates.map((c2, j) => (
                  <td key={`${c1}-${c2}`} className={i === j ? 'bg-slate-100' : ''}>
                    {i === j ? '-' : cellContent(c1, c2, i, j)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </CardBody>
  </Card>
);

export default PairwiseMatrixCard;
