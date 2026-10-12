// The static build (VITE_ENGINE=browser) has no Socket.IO: the panel runs its Monte Carlo
// over HTTP, which the engine in the page answers, and offers no streaming.
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MonteCarloResults from '../MonteCarloResults';
import { getMonteCarlo } from '../../../services/simulationCompareApi';

const start = vi.fn();

vi.mock('../../../api/browserEngine', () => ({ ENGINE_IN_BROWSER: true }));
vi.mock('../../../services/simulationCompareApi', () => ({
  getMonteCarlo: vi.fn(() => new Promise(() => {})),
}));
vi.mock('../../../hooks/useMonteCarloStream', () => ({
  useMonteCarloStream: () => ({
    progress: 0,
    iteration: 0,
    total: 0,
    partialResults: {},
    isRunning: false,
    error: null,
    regretHistory: {},
    agreementHistory: [],
    ciHalfLatest: {},
    iterationCheckpoints: [],
    start,
    stop: vi.fn(),
    reset: vi.fn(),
  }),
}));
vi.mock('../MonteCarloLiveChart', () => ({ default: () => null }));
vi.mock('../MonteCarloConvergencePanel', () => ({ default: () => null }));

it('runs over HTTP and offers no streaming switch', async () => {
  const { container } = render(<MonteCarloResults baseParams={{}} />);
  expect(container.querySelector('#streaming-toggle')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /monte carlo/i }));
  await waitFor(() => expect(getMonteCarlo).toHaveBeenCalledOnce());
  expect(start).not.toHaveBeenCalled();
});
