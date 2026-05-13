import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioConfigRow from '../ScenarioConfigRow';

describe('ScenarioConfigRow', () => {
  const baseConfig = {
    numVoters: 500,
    candidateInput: 'Alice, Bob',
    ideology_distribution: 'random',
  };
  const onChange = jest.fn();

  it('renders candidate input, voters, and distribution', () => {
    render(<ScenarioConfigRow config={baseConfig} onChange={onChange} />);
    expect(screen.getByDisplayValue('Alice, Bob')).toBeInTheDocument();
    expect(screen.getByDisplayValue('500')).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(<ScenarioConfigRow config={baseConfig} onChange={onChange} label="Scenario A" />);
    expect(screen.getByText('Scenario A')).toBeInTheDocument();
  });

  it('calls onChange when candidate input changes', () => {
    render(<ScenarioConfigRow config={baseConfig} onChange={onChange} />);
    const input = screen.getByDisplayValue('Alice, Bob');
    fireEvent.change(input, { target: { value: 'Alice, Bob, Charlie' } });
    expect(onChange).toHaveBeenCalledWith({ candidateInput: 'Alice, Bob, Charlie' });
  });

  it('calls onChange when voters input changes', () => {
    render(<ScenarioConfigRow config={baseConfig} onChange={onChange} />);
    const input = screen.getByDisplayValue('500');
    fireEvent.change(input, { target: { value: '1000' } });
    expect(onChange).toHaveBeenCalledWith({ numVoters: 1000 });
  });
});
