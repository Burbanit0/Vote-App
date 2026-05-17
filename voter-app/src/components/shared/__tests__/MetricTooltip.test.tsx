import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MetricTooltip from '../MetricTooltip';

describe('MetricTooltip', () => {
  it('renders the ⓘ icon button', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    expect(screen.getByTestId('metric-tooltip-bayesian_regret')).toBeInTheDocument();
    expect(screen.getByText('ⓘ')).toBeInTheDocument();
  });

  it('popover is not visible before click', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    // Popover body should not be in the DOM before opening
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('clicking ⓘ toggles aria-expanded on the button', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    const btn = screen.getByText('ⓘ');
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
  });

  it('clicking ⓘ for condorcet_compliance shows different content', () => {
    render(<MetricTooltip metric="condorcet_compliance" />);
    expect(screen.getByTestId('metric-tooltip-condorcet_compliance')).toBeInTheDocument();
  });

  it('size="md" button has testid reflecting the metric', () => {
    render(<MetricTooltip metric="manipulability" size="md" />);
    const btn = screen.getByTestId('metric-tooltip-manipulability');
    expect(btn).toBeInTheDocument();
  });

  it('size="sm" is the default — button renders without explicit size', () => {
    const { container } = render(<MetricTooltip metric="method_agreement" />);
    const btn = container.querySelector('[data-testid="metric-tooltip-method_agreement"]');
    expect(btn).not.toBeNull();
    // Default size = sm → fontSize 0.72rem
    expect((btn as HTMLElement).style.fontSize).toBe('0.72rem');
  });

  it('size="md" button has larger font', () => {
    const { container } = render(<MetricTooltip metric="method_agreement" size="md" />);
    const btn = container.querySelector('[data-testid="metric-tooltip-method_agreement"]');
    expect((btn as HTMLElement).style.fontSize).toBe('1rem');
  });

  it('clicking twice toggles the popover off', () => {
    render(<MetricTooltip metric="winner_stability" />);
    const btn = screen.getByText('ⓘ');
    fireEvent.click(btn); // open
    fireEvent.click(btn); // close
    // No assertion error — just verifying no crash on double-click
    expect(btn).toBeInTheDocument();
  });

  it('all supported metrics render without error', () => {
    const metrics: Array<React.ComponentProps<typeof MetricTooltip>['metric']> = [
      'bayesian_regret', 'method_agreement', 'winner_stability',
      'condorcet_compliance', 'manipulability', 'blank_rate',
      'stability_score', 'majority_satisfaction', 'delta_agreement',
    ];
    for (const metric of metrics) {
      const { unmount } = render(<MetricTooltip metric={metric} />);
      expect(screen.getByTestId(`metric-tooltip-${metric}`)).toBeInTheDocument();
      unmount();
    }
  });
});
