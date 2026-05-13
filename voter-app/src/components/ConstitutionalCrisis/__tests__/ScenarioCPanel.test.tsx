import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioCPanel from '../ScenarioCPanel';

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: () => <div />,
  CartesianGrid: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
}));

describe('ScenarioCPanel', () => {
  it('renders seat count slider', () => {
    render(<ScenarioCPanel result={null} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/Nombre de sièges/)).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('renders run button', () => {
    render(<ScenarioCPanel result={null} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/Composer l'assemblée/)).toBeInTheDocument();
  });

  it('renders results with chart and table', () => {
    const result = {
      party_votes: { A: 400, B: 300, C: 200 },
      multiwinner: {
        dhondt: { seats: { A: 45, B: 33, C: 22 }, metrics: { gallagher_index: 0.03 } },
        sainte_lague: { seats: { A: 44, B: 34, C: 22 }, metrics: { gallagher_index: 0.02 } },
        comparison: { most_proportional: 'sainte_lague' },
      },
      conclusion: 'Sainte-Laguë est le plus proportionnel.',
    };
    render(<ScenarioCPanel result={result as any} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/Sainte-Laguë est le plus proportionnel/)).toBeInTheDocument();
    expect(screen.getByText("D'Hondt")).toBeInTheDocument();
    expect(screen.getByText('Sainte-Laguë')).toBeInTheDocument();
  });

  it('shows uninominal comparison when available', () => {
    const result = {
      party_votes: { A: 400, B: 300 },
      uninominal_winner: 'A',
      multiwinner: {
        dhondt: { seats: { A: 50, B: 50 }, metrics: { gallagher_index: 0.05 } },
      },
      conclusion: 'Test',
    };
    render(<ScenarioCPanel result={result as any} loading={false} onRun={jest.fn()} />);
    expect(screen.getAllByText(/Scrutin uninominal/).length).toBeGreaterThanOrEqual(1);
  });
});
