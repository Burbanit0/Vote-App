import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BlankVoteRuleSelector from '../BlankVoteRuleSelector';

describe('BlankVoteRuleSelector', () => {
  const defaultProps = {
    selected: 'symbolic' as const,
    onChange: jest.fn(),
    hasBlankCandidate: true,
  };

  it('renders all rule cards', () => {
    render(<BlankVoteRuleSelector {...defaultProps} />);
    expect(screen.getByText('Symbolique')).toBeInTheDocument();
    expect(screen.getByText('Compétitif')).toBeInTheDocument();
    expect(screen.getByText('Seuil 30%')).toBeInTheDocument();
    expect(screen.getByText('Majorité requise')).toBeInTheDocument();
  });

  it('calls onChange when clicking a rule', () => {
    const onChange = jest.fn();
    render(<BlankVoteRuleSelector {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByText('Compétitif'));
    expect(onChange).toHaveBeenCalledWith('competitive');
  });

  it('shows warning when hasBlankCandidate is false', () => {
    render(<BlankVoteRuleSelector {...defaultProps} hasBlankCandidate={false} />);
    expect(screen.getByText(/Vous n'avez pas ajouté le Vote Blanc/)).toBeInTheDocument();
  });

  it('shows checkmark on selected rule', () => {
    render(<BlankVoteRuleSelector {...defaultProps} selected="symbolic" />);
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('shows selected rule label in footer', () => {
    render(<BlankVoteRuleSelector {...defaultProps} selected="competitive" />);
    expect(screen.getByText(/Règle sélectionnée/)).toBeInTheDocument();
  });
});
