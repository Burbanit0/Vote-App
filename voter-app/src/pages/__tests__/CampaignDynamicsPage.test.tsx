import { render, screen, within, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Stub the heavy temporal anchor — this suite tests the page shell + hand-off,
// not the migrated panels (those keep their own tests).
vi.mock('../../components/playground/anchors/CampaignAnchor', () => ({
  default: () => <div data-testid="campaign-anchor-stub" />,
}));

import { MemoryRouter } from 'react-router';
import CampaignDynamicsPage from '../CampaignDynamicsPage';
import {
  useElectionStore,
  DEFAULT_PLAYGROUND,
  DEFAULT_CONFIG,
} from '../../stores/useElectionStore';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/campagne']}>
      <CampaignDynamicsPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    playground: { ...DEFAULT_PLAYGROUND },
    config: { ...DEFAULT_CONFIG },
  });
});

describe('CampaignDynamicsPage (C1 shell + hand-off)', () => {
  it('renders the page with the sandbox badge', () => {
    renderPage();
    expect(screen.getByTestId('campaign-dynamics-page')).toBeInTheDocument();
    expect(screen.getByTestId('sandbox-badge')).toBeInTheDocument();
  });

  it('inherits the electorate (J0) from the shared store — names + counts', () => {
    renderPage();
    // Scope to the inherited-electorate card (names also appear in the timeline).
    const card = within(screen.getByTestId('inherited-electorate'));
    // DEFAULT_CONFIG: Alice, Bob, Carol · 300 voters.
    for (const name of ['Alice', 'Bob', 'Carol']) {
      expect(card.getByText(name)).toBeInTheDocument();
    }
    expect(card.getByText('300')).toBeInTheDocument();
  });

  it('reflects a different stored electorate (proves it reads the store, not a constant)', () => {
    useElectionStore.setState({
      config: {
        ...DEFAULT_CONFIG,
        candidates: [
          { name: 'Zoe', x: -0.2, y: 0 },
          { name: 'Yann', x: 0.3, y: 0.1 },
        ],
        num_voters: 512,
      },
    });
    renderPage();
    const card = within(screen.getByTestId('inherited-electorate'));
    expect(card.getByText('Zoe')).toBeInTheDocument();
    expect(card.getByText('Yann')).toBeInTheDocument();
    expect(card.getByText('512')).toBeInTheDocument();
  });

  it('is a sandbox — rendering the page does not mutate the shared config', () => {
    const before = JSON.stringify(useElectionStore.getState().config);
    renderPage();
    expect(JSON.stringify(useElectionStore.getState().config)).toBe(before);
  });

  it('pin writes the current (drifted) positions back into the shared config', () => {
    renderPage();
    const before = useElectionStore.getState().config.candidates.map((c) => ({ ...c }));
    fireEvent.click(screen.getByTestId('round-stop-3')); // scrub to end → full drift
    fireEvent.click(screen.getByTestId('timeline-pin'));
    const after = useElectionStore.getState().config.candidates;
    // Same candidates (by name), but at least one position changed.
    expect(after.map((c) => c.name)).toEqual(before.map((c) => c.name));
    const moved = after.some((c, i) => Math.abs(c.x - before[i].x) > 1e-6);
    expect(moved).toBe(true);
  });

  it('offers a way back to the playground', () => {
    renderPage();
    const back = screen.getByTestId('back-to-playground');
    expect(back).toHaveAttribute('href', '/playground');
  });

  it('shows an empty state (and a path back) when no electorate is configured', () => {
    useElectionStore.setState({ config: { ...DEFAULT_CONFIG, candidates: [] } });
    renderPage();
    expect(screen.getByTestId('empty-electorate')).toBeInTheDocument();
    // Neither the instrument nor the explorations drawer render without an electorate.
    expect(screen.queryByTestId('campaign-explorations-toggle')).not.toBeInTheDocument();
  });

  it('mounts the instrument and the (collapsed) explorations drawer with an electorate', () => {
    renderPage();
    expect(screen.getByTestId('campaign-timeline')).toBeInTheDocument();
    // The deep panels are demoted into one collapsed drawer (form-lock: not mounted).
    expect(screen.getByTestId('campaign-explorations-toggle')).toBeInTheDocument();
  });
});
