import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));

import PlaygroundPage from '../PlaygroundPage';
import { useElectionStore, DEFAULT_PLAYGROUND, DEFAULT_CONFIG } from '../../stores/useElectionStore';

const LS_PG = 'votelab_playground';

beforeEach(() => {
  localStorage.clear();
  // Reset the module-singleton store to a known baseline between tests.
  useElectionStore.setState({ playground: { ...DEFAULT_PLAYGROUND }, config: { ...DEFAULT_CONFIG } });
});

describe('PlaygroundPage (P0 shell)', () => {
  it('renders and shows the leader canvas by default', () => {
    render(<PlaygroundPage />);
    expect(screen.getByTestId('playground-page')).toBeInTheDocument();
    expect(screen.getByTestId('canvas-leader')).toBeInTheDocument();
    expect(screen.queryByTestId('canvas-parliament')).not.toBeInTheDocument();
  });

  it('mode toggle swaps the canvas, reveals assembly knobs, and persists', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('mode-toggle-parliament'));

    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.queryByTestId('canvas-leader')).not.toBeInTheDocument();
    // Assembly-only knob appears in parliament mode.
    expect(screen.getByLabelText('Structure')).toBeInTheDocument();

    expect(useElectionStore.getState().playground.mode).toBe('parliament');
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).mode).toBe('parliament');
  });

  it('a preset mutates shared electorate + playground state and persists', () => {
    render(<PlaygroundPage />);
    fireEvent.click(screen.getByTestId('preset-fragmented'));

    const { playground, config } = useElectionStore.getState();
    expect(playground.mode).toBe('parliament');
    expect(config.candidates).toHaveLength(6);
    expect(config.num_voters).toBe(600);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).mode).toBe('parliament');
    // The canvas reflects the preset's mode.
    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
  });

  it('a knob change (dimensions) persists to the store', () => {
    render(<PlaygroundPage />);
    fireEvent.change(screen.getByLabelText('Dimensions de l’espace'), { target: { value: '3' } });

    expect(useElectionStore.getState().playground.space.dims).toBe(3);
    expect(JSON.parse(localStorage.getItem(LS_PG) as string).space.dims).toBe(3);
  });
});
