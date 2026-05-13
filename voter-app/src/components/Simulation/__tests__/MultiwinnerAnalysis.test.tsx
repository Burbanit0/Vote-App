import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MultiwinnerAnalysis from '../MultiwinnerAnalysis';

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: () => <div />,
  CartesianGrid: () => <div />,
  Cell: () => <div />,
  Legend: () => <div />,
  ReferenceLine: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}));

jest.mock('../../shared/ResponsiveTable', () => ({ children, className }: any) => <div className={className}>{children}</div>);
jest.mock('../../../services/simulationCompareApi', () => ({
  getMultiwinner: jest.fn(),
}));

describe('MultiwinnerAnalysis', () => {
  it('renders config form', () => {
    render(<MultiwinnerAnalysis />);
    expect(screen.getByText('Seats to fill')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Analyse/ })).toBeInTheDocument();
  });

  it('renders results when getMultiwinner resolves', async () => {
    const { getMultiwinner } = jest.requireMock('../../../services/simulationCompareApi');
    const mockMethod = (seatsA: number, seatsB: number, gallagher: number) => ({
      seats: { A: seatsA, B: seatsB },
      metrics: {
        gallagher_index: gallagher,
        effective_parties_seats: 2.0,
        effective_parties_votes: 2.0,
        largest_deviation: { party: 'A', deviation: 0 },
      },
    });
    (getMultiwinner as jest.Mock).mockResolvedValue({
      party_votes: { A: 50, B: 50 },
      num_seats: 20,
      dhondt: mockMethod(10, 10, 0.05),
      sainte_lague: mockMethod(11, 9, 0.02),
      largest_remainder_hare: mockMethod(10, 10, 0.04),
      largest_remainder_droop: mockMethod(10, 10, 0.03),
      comparison: {
        most_proportional: 'sainte_lague',
        least_proportional: 'dhondt',
        gallagher_ranking: ['sainte_lague', 'largest_remainder_droop', 'largest_remainder_hare', 'dhondt'],
      },
    });

    render(<MultiwinnerAnalysis />);
    const button = screen.getByRole('button', { name: /Analyse/ });
    fireEvent.click(button);

    expect(await screen.findByText(/Most proportional/)).toBeInTheDocument();
  });
});
