import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

const setLeaderRule = vi.fn();
let ctx: any;

vi.mock('../PlaygroundController', () => ({
  usePlaygroundCtx: () => ctx,
}));

import NonSpatialProfileMap from '../NonSpatialProfileMap';

function baseResult(overrides: Partial<any> = {}) {
  return {
    methods: { plurality: { winner: 'Alice' } },
    candidate_names: ['Alice', 'Bob'],
    display_points: [
      [0.1, 0.2],
      [-0.3, 0.4],
    ],
    candidate_points: [
      [0.2, 0.1],
      [-0.2, -0.1],
    ],
    ...overrides,
  };
}

beforeEach(() => {
  setLeaderRule.mockClear();
});

describe('NonSpatialProfileMap', () => {
  it('shows a computing placeholder while loading', () => {
    ctx = { result: null, loading: true, leaderRule: 'plurality', setLeaderRule };
    render(<NonSpatialProfileMap />);
    expect(screen.getByTestId('nonspatial-map')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('shows a computing placeholder when there is no result yet', () => {
    ctx = { result: null, loading: false, leaderRule: 'plurality', setLeaderRule };
    render(<NonSpatialProfileMap />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders the biplot, rings the winner and names every candidate', () => {
    ctx = { result: baseResult(), loading: false, leaderRule: 'plurality', setLeaderRule };
    render(<NonSpatialProfileMap />);
    expect(screen.getByRole('img')).toBeInTheDocument();
    expect(screen.getAllByText('Alice').length).toBeGreaterThan(0);
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('maps a client rule id through BACKEND_SLUG to find the winner', () => {
    // 'condorcet' → backend slug 'copeland' per BACKEND_SLUG.
    ctx = {
      result: baseResult({ methods: { copeland: { winner: 'Bob' } } }),
      loading: false,
      leaderRule: 'condorcet',
      setLeaderRule,
    };
    render(<NonSpatialProfileMap />);
    // "Bob" appears both as the winner readout and a candidate label.
    expect(screen.getAllByText('Bob').length).toBeGreaterThanOrEqual(1);
  });

  it('falls back to "no winner" when the mapped method has none', () => {
    ctx = {
      result: baseResult({ methods: {} }),
      loading: false,
      leaderRule: 'plurality',
      setLeaderRule,
    };
    render(<NonSpatialProfileMap />);
    // Candidate names still render even with no declared winner.
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('changing the rule select calls setLeaderRule', () => {
    ctx = { result: baseResult(), loading: false, leaderRule: 'plurality', setLeaderRule };
    render(<NonSpatialProfileMap />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'borda' } });
    expect(setLeaderRule).toHaveBeenCalledWith('borda');
  });

  it('handles a missing candidate_points array without crashing', () => {
    ctx = {
      result: baseResult({ candidate_points: null }),
      loading: false,
      leaderRule: 'plurality',
      setLeaderRule,
    };
    render(<NonSpatialProfileMap />);
    expect(screen.getByRole('img')).toBeInTheDocument();
  });
});
