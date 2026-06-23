import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
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

  it('shows no pin button without onPin (pure sandbox)', () => {
    renderTimeline();
    expect(screen.queryByTestId('timeline-pin')).not.toBeInTheDocument();
  });

  it('pins the drifted candidates back via onPin (J0 = original positions)', () => {
    const onPin = vi.fn();
    render(
      <CampaignTimeline config={DEFAULT_CONFIG} playground={DEFAULT_PLAYGROUND} onPin={onPin} />
    );
    fireEvent.click(screen.getByTestId('timeline-pin'));
    expect(onPin).toHaveBeenCalledTimes(1);
    const pinned = onPin.mock.calls[0][0];
    // At J0 (default t) the pinned positions equal the inherited candidates.
    expect(pinned.map((c: { name: string }) => c.name)).toEqual(
      DEFAULT_CONFIG.candidates.map((c) => c.name)
    );
    expect(pinned[0].x).toBeCloseTo(DEFAULT_CONFIG.candidates[0].x);
    // Confirmation appears.
    expect(screen.getByText(/Positions reportées/)).toBeInTheDocument();
  });

  it('pins drifted (moved) positions after scrubbing to the end', () => {
    const onPin = vi.fn();
    render(
      <CampaignTimeline config={DEFAULT_CONFIG} playground={DEFAULT_PLAYGROUND} onPin={onPin} />
    );
    fireEvent.click(screen.getByTestId('round-stop-3')); // t = 1 → full drift
    fireEvent.click(screen.getByTestId('timeline-pin'));
    const pinned = onPin.mock.calls[0][0];
    // At least one candidate moved from its J0 position.
    const moved = pinned.some(
      (c: { x: number }, i: number) => Math.abs(c.x - DEFAULT_CONFIG.candidates[i].x) > 1e-6
    );
    expect(moved).toBe(true);
  });
});
