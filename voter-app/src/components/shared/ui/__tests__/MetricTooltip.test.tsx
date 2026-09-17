import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MetricTooltip from '../MetricTooltip';

// The ⓘ mechanics live in InfoPopover (see its own callers' tests); what is
// specific here is that each metric key resolves to its own content.

describe('MetricTooltip', () => {
  it('renders the ⓘ icon button', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    expect(screen.getByTestId('info-metric-bayesian_regret')).toBeInTheDocument();
    expect(screen.getByText('ⓘ')).toBeInTheDocument();
  });

  it('popover is not visible before click', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('clicking ⓘ toggles aria-expanded on the button', () => {
    render(<MetricTooltip metric="bayesian_regret" />);
    const btn = screen.getByText('ⓘ');
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
  });

  it('opens a popover carrying the metric title and its plain-language line', () => {
    render(<MetricTooltip metric="condorcet_compliance" />);
    fireEvent.click(screen.getByText('ⓘ'));
    const pop = screen.getByTestId('pop-metric-condorcet_compliance');
    expect(pop).toHaveTextContent('Condorcet Compliance');
    expect(pop).toHaveTextContent('beat all others in direct head-to-head matchups');
  });

  it('labels the button for screen readers with the metric title', () => {
    render(<MetricTooltip metric="manipulability" />);
    expect(screen.getByTestId('info-metric-manipulability')).toHaveAttribute(
      'aria-label',
      'Metric information: Strategic Vulnerability'
    );
  });

  it('clicking twice toggles the popover off', () => {
    render(<MetricTooltip metric="winner_stability" />);
    const btn = screen.getByText('ⓘ');
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('all supported metrics render without error', () => {
    const metrics: Array<React.ComponentProps<typeof MetricTooltip>['metric']> = [
      'bayesian_regret',
      'method_agreement',
      'winner_stability',
      'condorcet_compliance',
      'manipulability',
      'blank_rate',
      'stability_score',
      'majority_satisfaction',
      'delta_agreement',
    ];
    for (const metric of metrics) {
      const { unmount } = render(<MetricTooltip metric={metric} />);
      expect(screen.getByTestId(`info-metric-${metric}`)).toBeInTheDocument();
      unmount();
    }
  });
});
