import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BlankVoteRuleSelector from '../BlankVoteRuleSelector';

describe('BlankVoteRuleSelector', () => {
  const defaultProps = {
    selected: 'symbolic' as const,
    onChange: vi.fn(),
    hasBlankCandidate: true,
  };

  it('renders all rule cards', () => {
    render(<BlankVoteRuleSelector {...defaultProps} />);
    expect(screen.getByText('Symbolic')).toBeInTheDocument();
    expect(screen.getByText('Competitive')).toBeInTheDocument();
    expect(screen.getByText('30% Threshold')).toBeInTheDocument();
    expect(screen.getByText('Majority required')).toBeInTheDocument();
  });

  it('calls onChange when clicking a rule', () => {
    const onChange = vi.fn();
    render(<BlankVoteRuleSelector {...defaultProps} onChange={onChange} />);
    fireEvent.click(screen.getByText('Competitive'));
    expect(onChange).toHaveBeenCalledWith('competitive');
  });

  it('shows warning when hasBlankCandidate is false', () => {
    render(<BlankVoteRuleSelector {...defaultProps} hasBlankCandidate={false} />);
    expect(screen.getByText(/have not added the Blank Vote/)).toBeInTheDocument();
  });

  it('shows checkmark on selected rule', () => {
    render(<BlankVoteRuleSelector {...defaultProps} selected="symbolic" />);
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('shows selected rule label in footer', () => {
    render(<BlankVoteRuleSelector {...defaultProps} selected="competitive" />);
    expect(screen.getByText(/Selected rule/)).toBeInTheDocument();
  });
});
