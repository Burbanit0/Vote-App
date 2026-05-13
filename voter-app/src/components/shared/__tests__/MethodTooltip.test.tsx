import React from 'react';
import { render, screen } from '@testing-library/react';
import MethodTooltip from '../MethodTooltip';

jest.mock('../../Simulation/simulationConstants', () => ({
  useMethodLabels: () => ({ plurality: 'Plurality' }),
  useMethodPros: () => ({ plurality: 'Simple and universal' }),
  useMethodCons: () => ({ plurality: 'Creates spoiler effect' }),
  METHOD_DESCRIPTIONS: {
    plurality: 'Each voter votes for one candidate.',
    unknown_method: undefined as string | undefined,
  },
}));

describe('MethodTooltip', () => {
  it('renders label from methodLabels when no children', () => {
    render(<MethodTooltip method="plurality" />);
    expect(screen.getByText('Plurality')).toBeInTheDocument();
  });

  it('renders children instead of label', () => {
    render(<MethodTooltip method="plurality">Custom Label</MethodTooltip>);
    expect(screen.getByText('Custom Label')).toBeInTheDocument();
  });

  it('renders plain span when no description exists', () => {
    render(<MethodTooltip method="unknown_method">Fallback</MethodTooltip>);
    const span = screen.getByText('Fallback');
    expect(span.tagName).toBe('SPAN');
    expect(span.closest('[role="button"]')).toBeNull();
  });

  it('renders OverlayTrigger with tooltip when description exists', () => {
    render(<MethodTooltip method="plurality" />);
    const trigger = screen.getByRole('button');
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-label', 'Definition: Plurality');
  });
});
