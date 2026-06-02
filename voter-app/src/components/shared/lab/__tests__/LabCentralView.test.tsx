import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import LabCentralView from '../LabCentralView';
import { usePerturbations, useLabStore } from '../../../../stores/useLabStore';
import type { ElectionResult } from '../../../../services/electionApi';

// Mock the heavy ideology map (it does an axios fetch on mount)
vi.mock('../../../Simulation/IdeologyMapChart', () => ({ default: () => (
  <div data-testid="mock-map">map</div>
) }));

const COLLAPSED_LS_KEY = 'votelab_central_collapsed';
const FOCUS_LS_KEY     = 'votelab_central_focus_mode';

function makeResult(): ElectionResult {
  return {
    config: {
      candidates: [
        { name: 'Alice', x: -0.5, y: 0.2, party: 'Liberal' },
        { name: 'Bob',   x:  0.5, y: 0.0, party: 'Conservative' },
      ],
      num_voters: 100,
      ideology: 'random',
      seed: 42,
    } as any,
    candidates: [
      { name: 'Alice', x: -0.5, y: 0.2, party: 'Liberal' },
      { name: 'Bob',   x:  0.5, y: 0.0, party: 'Conservative' },
    ] as any,
    methods: {
      plurality: { winner: 'Alice', vote_shares: { Alice: 0.6, Bob: 0.4 } } as any,
      irv:       { winner: 'Bob',   vote_shares: { Alice: 0.45, Bob: 0.55 } } as any,
    },
    condorcet_winner: 'Bob',
  } as unknown as ElectionResult;
}

// Perturbations + animation are store-backed (useLabStore) — no providers needed.
function wrap(children: React.ReactNode) {
  return <>{children}</>;
}

describe('LabCentralView', () => {
  beforeEach(() => {
    localStorage.clear();
    useLabStore.setState({ pinned: [], frame: null });
  });

  it('renders empty placeholder when result is null', () => {
    render(wrap(<LabCentralView result={null} loading={false} />));
    expect(screen.getByTestId('lab-central-empty')).toBeInTheDocument();
  });

  it('renders matrix and map when result is provided', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    expect(screen.getByTestId('lab-central-view')).toBeInTheDocument();
    expect(screen.getByTestId('lab-methods-matrix')).toBeInTheDocument();
    expect(screen.getByTestId('mock-map')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-plurality')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-row-irv')).toBeInTheDocument();
  });

  it('hides the map when focus mode is enabled', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    expect(screen.getByTestId('mock-map')).toBeInTheDocument();
    act(() => { fireEvent.click(screen.getByTestId('central-focus-toggle')); });
    expect(screen.queryByTestId('mock-map')).not.toBeInTheDocument();
    // Matrix still visible
    expect(screen.getByTestId('lab-methods-matrix')).toBeInTheDocument();
  });

  it('persists focus mode to localStorage', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    act(() => { fireEvent.click(screen.getByTestId('central-focus-toggle')); });
    expect(localStorage.getItem(FOCUS_LS_KEY)).toBe('1');
    act(() => { fireEvent.click(screen.getByTestId('central-focus-toggle')); });
    expect(localStorage.getItem(FOCUS_LS_KEY)).toBe('0');
  });

  it('restores focus mode from localStorage on mount', () => {
    localStorage.setItem(FOCUS_LS_KEY, '1');
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    expect(screen.queryByTestId('mock-map')).not.toBeInTheDocument();
  });

  it('collapses the body when collapse toggle clicked', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    expect(screen.getByTestId('central-body')).toBeInTheDocument();
    act(() => { fireEvent.click(screen.getByTestId('central-collapse-toggle')); });
    expect(screen.queryByTestId('central-body')).not.toBeInTheDocument();
  });

  it('persists collapsed state to localStorage', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    act(() => { fireEvent.click(screen.getByTestId('central-collapse-toggle')); });
    expect(localStorage.getItem(COLLAPSED_LS_KEY)).toBe('1');
  });

  it('switches to table layout when a perturbation with per-method winners is pinned', () => {
    const PinHelper: React.FC = () => {
      const { pinPerturbation } = usePerturbations();
      React.useEffect(() => {
        pinPerturbation({
          type:    'abstention',
          icon:    '🗳',
          label:   'Abst 50%',
          summary: 'Bob wins',
          methodsChanged: 1,
          winnersByMethod: { plurality: 'Bob', irv: 'Bob' },
        });
      }, [pinPerturbation]);
      return null;
    };
    render(wrap(
      <>
        <PinHelper />
        <LabCentralView result={makeResult()} loading={false} />
      </>
    ));
    expect(screen.getByTestId('lab-matrix-table')).toBeInTheDocument();
    expect(screen.getByTestId('matrix-col-abstention')).toBeInTheDocument();
    // Plurality baseline = Alice, perturbed = Bob → "changed" cell present
    expect(screen.getByTestId('matrix-pert-plurality-abstention')).toBeInTheDocument();
    // No table without pinned (default path)
    // (covered by other tests)
  });

  it('shows condorcet checkmark on the matrix row of the Condorcet winner', () => {
    render(wrap(<LabCentralView result={makeResult()} loading={false} />));
    const irvRow = screen.getByTestId('matrix-row-irv');
    // Bob is both IRV winner and Condorcet winner — ✓ should be inside that row
    expect(irvRow.textContent).toContain('✓');
    // Alice wins plurality but isn't Condorcet — no ✓
    const pluralityRow = screen.getByTestId('matrix-row-plurality');
    expect(pluralityRow.textContent).not.toContain('✓');
  });
});
