import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioAPanel from '../ScenarioAPanel';

jest.mock('../../ScenarioBuilder/CandidateEditor', () => {
  const MockEditor = ({ candidates, onChange }: any) => (
    <div data-testid="candidate-editor">
      {candidates.map((c: any) => (
        <div key={c.id}>
          <span>{c.name}</span>
          <button onClick={() => onChange(candidates.filter((x: any) => x.id !== c.id))}>✕</button>
        </div>
      ))}
    </div>
  );
  return Object.assign(MockEditor, { newCandidate: () => ({ id: 'new' }), newBlankCandidate: () => ({ id: 'blank', isBlank: true }) });
});

const initialCandidates = [
  { id: '1', name: 'Alice', ideology: 0.5, isBlank: false, economy: 0.5, environment: 0.5, social: 0.5 },
  { id: '2', name: 'Bob', ideology: -0.3, isBlank: false, economy: 0.5, environment: 0.5, social: 0.5 },
];

describe('ScenarioAPanel', () => {
  it('renders candidate editor', () => {
    render(<ScenarioAPanel initialCandidates={initialCandidates} result={null} loading={false} onRun={jest.fn()} />);
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('renders run button enabled when candidates exist', () => {
    render(<ScenarioAPanel initialCandidates={initialCandidates} result={null} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/Simuler le 2ème tour/)).toBeInTheDocument();
  });

  it('shows loading spinner when loading', () => {
    render(<ScenarioAPanel initialCandidates={initialCandidates} result={null} loading={true} onRun={jest.fn()} />);
    expect(screen.getByText(/Simulation…/)).toBeInTheDocument();
  });

  it('renders results when provided', () => {
    const result = {
      round1: {
        methods: { plurality: { winner: 'Alice' } },
      },
      round2: {
        methods: { plurality: { winner: 'Bob' } },
      },
      conclusion: 'Le second tour change le vainqueur.',
    };
    render(<ScenarioAPanel initialCandidates={initialCandidates} result={result as any} loading={false} onRun={jest.fn()} />);
    expect(screen.getByText(/Le second tour change le vainqueur/)).toBeInTheDocument();
  });
});
