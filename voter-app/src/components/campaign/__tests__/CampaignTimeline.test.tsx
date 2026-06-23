import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CampaignTimeline from '../CampaignTimeline';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../../stores/useElectionStore';

function renderTimeline() {
  return render(<CampaignTimeline config={DEFAULT_CONFIG} playground={DEFAULT_PLAYGROUND} />);
}

describe('CampaignTimeline (C2)', () => {
  it('renders the timeline, scrubber and trajectory', () => {
    renderTimeline();
    expect(screen.getByTestId('campaign-timeline')).toBeInTheDocument();
    expect(screen.getByTestId('timeline-scrubber')).toBeInTheDocument();
    expect(screen.getByTestId('campaign-trajectory')).toBeInTheDocument();
  });

  it('shows a current winner drawn from the inherited candidates', () => {
    renderTimeline();
    const winner = screen.getByTestId('timeline-winner').textContent;
    expect(['Alice', 'Bob', 'Carol']).toContain(winner);
  });

  it('reports a Condorcet verdict and both quality meters', () => {
    renderTimeline();
    expect(screen.getByTestId('timeline-condorcet')).toBeInTheDocument();
    expect(screen.getByTestId('timeline-regret')).toBeInTheDocument();
    expect(screen.getByTestId('timeline-congruence')).toBeInTheDocument();
  });

  it('renders one discrete round stop per round (default 4)', () => {
    renderTimeline();
    for (let i = 0; i < 4; i++) {
      expect(screen.getByTestId(`round-stop-${i}`)).toBeInTheDocument();
    }
    expect(screen.queryByTestId('round-stop-4')).not.toBeInTheDocument();
  });

  it('clicking the last round stop scrubs to the end of the campaign (J{numDays})', () => {
    renderTimeline();
    const scrubber = screen.getByTestId('timeline-scrubber') as HTMLInputElement;
    expect(scrubber.value).toBe('0');
    fireEvent.click(screen.getByTestId('round-stop-3')); // t = 1
    expect(scrubber.value).toBe('1');
    // Day readout reaches J30 (DEFAULT campaign num_days) in the winner card.
    expect(within(screen.getByTestId('timeline-readout')).getByText(/J30/)).toBeInTheDocument();
  });

  it('the round stepper is bounded (prev disabled at T1, next disabled at TN)', () => {
    renderTimeline();
    // At J0 the active stop is T1 → prev disabled.
    expect(screen.getByTestId('round-prev')).toBeDisabled();
    // Step to the last round → next disabled.
    fireEvent.click(screen.getByTestId('round-stop-3'));
    expect(screen.getByTestId('round-next')).toBeDisabled();
  });

  it('reset returns to J0', () => {
    renderTimeline();
    const scrubber = screen.getByTestId('timeline-scrubber') as HTMLInputElement;
    fireEvent.click(screen.getByTestId('round-stop-3'));
    expect(scrubber.value).toBe('1');
    fireEvent.click(screen.getByTestId('timeline-reset'));
    expect(scrubber.value).toBe('0');
  });

  it('changing the method re-evaluates without crashing', () => {
    renderTimeline();
    fireEvent.change(screen.getByTestId('timeline-rule'), { target: { value: 'minimax' } });
    // A winner is still resolved under the new rule.
    const readout = within(screen.getByTestId('timeline-readout'));
    expect(readout.getByTestId('timeline-winner').textContent).toBeTruthy();
  });
});
