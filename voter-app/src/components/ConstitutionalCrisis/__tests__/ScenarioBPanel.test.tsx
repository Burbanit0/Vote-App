import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioBPanel from '../ScenarioBPanel';

const candidateNames = ['Alice', 'Bob', 'Charlie'];

describe('ScenarioBPanel', () => {
  it('renders duration and drift controls', () => {
    render(<ScenarioBPanel candidateNames={candidateNames} result={null} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText('3 months')).toBeInTheDocument();
    expect(screen.getByText('6 months')).toBeInTheDocument();
    expect(screen.getByText(/Ideological drift amplitude/)).toBeInTheDocument();
  });

  it('calls onRun with correct params', () => {
    const onRun = jest.fn();
    render(<ScenarioBPanel candidateNames={candidateNames} result={null} loading={false} onRun={onRun} />);
    fireEvent.click(screen.getByText(/Simulate after provisional period/));
    expect(onRun).toHaveBeenCalledWith(3, 0.05);
  });

  it('renders results when provided', () => {
    const result = {
      before_drift: {
        methods: { plurality: { winner: 'Alice' } },
        blank_pct: 0.05,
      },
      after_drift: {
        methods: { plurality: { winner: 'Bob' } },
        blank_pct: 0.08,
      },
      conclusion: 'La dérive change le vainqueur.',
    };
    render(<ScenarioBPanel candidateNames={candidateNames} result={result as any} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/La dérive change le vainqueur/)).toBeInTheDocument();
    expect(screen.getByText(/5% → 8%/)).toBeInTheDocument();
  });
});
