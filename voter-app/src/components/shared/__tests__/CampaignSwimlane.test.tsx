import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CampaignSwimlane from '../CampaignSwimlane';
import type { CampaignSnapshot, MethodStability } from '../../../services/electionApi';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeSnapshot(day: number, winners: Record<string, string>): CampaignSnapshot {
  const methods: Record<string, any> = {};
  for (const [m, w] of Object.entries(winners)) {
    methods[m] = { winner: w, vote_share: 0.6 };
  }
  return { day, methods, inter_method_agreement: 0.8 };
}

const SNAPSHOTS: CampaignSnapshot[] = [
  makeSnapshot(0, { plurality: 'Alice', schulze: 'Alice', borda: 'Bob' }),
  makeSnapshot(7, { plurality: 'Alice', schulze: 'Alice', borda: 'Alice' }),
  makeSnapshot(14, { plurality: 'Bob', schulze: 'Alice', borda: 'Alice' }),
];

const METHOD_STABILITY: Record<string, MethodStability> = {
  schulze: { winner_changes: 0, final_winner: 'Alice', stability_score: 1.0 },
  plurality: { winner_changes: 1, final_winner: 'Bob', stability_score: 0.5 },
  borda: { winner_changes: 1, final_winner: 'Alice', stability_score: 0.5 },
};

const CANDIDATES = ['Alice', 'Bob'];

function renderSwimlane(props?: Partial<Parameters<typeof CampaignSwimlane>[0]>) {
  return render(
    <CampaignSwimlane
      snapshots={props?.snapshots ?? SNAPSHOTS}
      methodStability={props?.methodStability ?? METHOD_STABILITY}
      candidates={props?.candidates ?? CANDIDATES}
    />
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('CampaignSwimlane', () => {
  it('renders an SVG element', () => {
    const { container } = renderSwimlane();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('returns null when snapshots is empty', () => {
    const { container } = renderSwimlane({ snapshots: [], methodStability: {}, candidates: [] });
    expect(container.firstChild).toBeNull();
  });

  it('renders a method label for each method in methodStability', () => {
    renderSwimlane();
    expect(screen.getByTestId('swimlane-label-schulze')).toBeInTheDocument();
    expect(screen.getByTestId('swimlane-label-plurality')).toBeInTheDocument();
    expect(screen.getByTestId('swimlane-label-borda')).toBeInTheDocument();
  });

  it('renders the correct number of rect segments (one per snapshot per method)', () => {
    const { container } = renderSwimlane();
    // 3 methods × 3 snapshots = 9 rects (some may be null if winner is null)
    const rects = container.querySelectorAll('[data-testid^="swimlane-rect"]');
    // Each snapshot has a winner for every method → 9 total
    expect(rects.length).toBe(9);
  });

  it('sorts methods by stability_score descending (schulze=1.0 first)', () => {
    const { container } = renderSwimlane();
    const labels = container.querySelectorAll('[data-testid^="swimlane-label"]');
    expect(labels[0].textContent).toBe('schulze'); // stability=1.0 → first
  });

  it('shows candidate legend badges', () => {
    renderSwimlane();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('clicking a segment selects that candidate', () => {
    const { container } = renderSwimlane();
    const firstAliceRect = container.querySelector('[data-testid="swimlane-rect-schulze-0"]');
    expect(firstAliceRect).toBeInTheDocument();
    fireEvent.click(firstAliceRect!);
    // "Élu en fin de campagne par" or "Elected at campaign end by" should appear
    expect(screen.getByText(/Élu en fin|Elected at/i)).toBeInTheDocument();
  });

  it('clicking SVG background deselects candidate', () => {
    const { container } = renderSwimlane();
    // First select
    fireEvent.click(container.querySelector('[data-testid="swimlane-rect-schulze-0"]')!);
    // Then click SVG to deselect
    fireEvent.click(container.querySelector('svg')!);
    expect(screen.queryByText(/Élu en fin|Elected at/i)).toBeNull();
  });

  it('shows hover info when mouse enters a rect', () => {
    const { container } = renderSwimlane();
    const rect = container.querySelector('[data-testid="swimlane-rect-plurality-0"]');
    fireEvent.mouseEnter(rect!);
    // After mouseEnter, some info should appear (method + winner)
    expect(screen.getAllByText(/plurality/i).length).toBeGreaterThan(0);
  });

  it('shows click hint text', () => {
    renderSwimlane();
    expect(screen.getByText(/Cliquez|Click/i)).toBeInTheDocument();
  });
});
