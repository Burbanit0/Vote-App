import { renderHook, act } from '@testing-library/react';
import { useMonteCarloStream } from './useMonteCarloStream';

jest.mock('socket.io-client', () => {
  const mockSocket = {
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
  };
  return {
    io: jest.fn(() => mockSocket),
  };
});

const { io } = jest.requireMock('socket.io-client');

beforeEach(() => {
  jest.clearAllMocks();
});

function getSocket() {
  return io();
}

describe('useMonteCarloStream', () => {
  it('starts with initial state', () => {
    const { result } = renderHook(() => useMonteCarloStream());
    expect(result.current.progress).toBe(0);
    expect(result.current.iteration).toBe(0);
    expect(result.current.isRunning).toBe(false);
    expect(result.current.complete).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('start() creates a socket and emits start_monte_carlo on connect', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    expect(io).toHaveBeenCalledWith('http://localhost:4433', {
      transports: ['websocket', 'polling'],
    });

    const socket = getSocket();
    expect(result.current.isRunning).toBe(true);
    expect(result.current.total).toBe(50);

    const connectHandler = socket.on.mock.calls.find(
      ([event]: [string]) => event === 'connect'
    );
    expect(connectHandler).toBeDefined();

    connectHandler[1]();

    expect(socket.emit).toHaveBeenCalledWith('start_monte_carlo', {
      num_iterations: 50,
      num_voters: 200,
    });
  });

  it('updates state on progress event', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 100, num_voters: 200 });
    });

    const socket = getSocket();
    const progressHandler = socket.on.mock.calls.find(
      ([event]: [string]) => event === 'monte_carlo_progress'
    );

    act(() => {
      progressHandler[1]({
        iteration: 25,
        total: 100,
        partial_results: {
          plurality: { winner_distribution: { Alice: 0.6 }, most_common_winner: 'Alice' },
        },
        condorcet_exists_rate: 0.8,
      });
    });

    expect(result.current.iteration).toBe(25);
    expect(result.current.progress).toBe(25);
    expect(result.current.partialResults).toEqual({
      plurality: { winner_distribution: { Alice: 0.6 }, most_common_winner: 'Alice' },
    });
    expect(result.current.condorcetRate).toBe(0.8);
  });

  it('handles complete event', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket = getSocket();
    const completeHandler = socket.on.mock.calls.find(
      ([event]: [string]) => event === 'monte_carlo_complete'
    );

    act(() => {
      completeHandler[1]({
        final_results: {
          borda: { winner_distribution: { Alice: 0.7, Bob: 0.3 }, most_common_winner: 'Alice' },
        },
        num_iterations: 50,
        num_voters: 200,
        condorcet_exists_rate: 0.9,
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.progress).toBe(100);
    expect(result.current.complete).toEqual({
      final_results: {
        borda: { winner_distribution: { Alice: 0.7, Bob: 0.3 }, most_common_winner: 'Alice' },
      },
      num_iterations: 50,
      num_voters: 200,
      condorcet_exists_rate: 0.9,
    });
    expect(socket.disconnect).toHaveBeenCalled();
  });

  it('handles error event', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket = getSocket();
    const errorHandler = socket.on.mock.calls.find(
      ([event]: [string]) => event === 'monte_carlo_error'
    );

    act(() => {
      errorHandler[1]({ message: 'Simulation failed' });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe('Simulation failed');
    expect(socket.disconnect).toHaveBeenCalled();
  });

  it('handles connect_error', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket = getSocket();
    const connErrHandler = socket.on.mock.calls.find(
      ([event]: [string]) => event === 'connect_error'
    );

    act(() => {
      connErrHandler[1](new Error('Connection refused'));
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe('WebSocket connection failed');
  });

  it('stop() disconnects and sets isRunning false', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket = getSocket();
    expect(result.current.isRunning).toBe(true);

    act(() => {
      result.current.stop();
    });

    expect(socket.emit).toHaveBeenCalledWith('stop_monte_carlo', {});
    expect(socket.disconnect).toHaveBeenCalled();
    expect(result.current.isRunning).toBe(false);
  });

  it('reset() clears state and disconnects', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket = getSocket();

    act(() => {
      result.current.reset();
    });

    expect(socket.disconnect).toHaveBeenCalled();
    expect(result.current).toEqual({
      progress: 0,
      iteration: 0,
      total: 0,
      partialResults: {},
      condorcetRate: 0,
      isRunning: false,
      complete: null,
      error: null,
      regretHistory: {},
      agreementHistory: [],
      ciHalfLatest: {},
      iterationCheckpoints: [],
      start: expect.any(Function),
      stop: expect.any(Function),
      reset: expect.any(Function),
    });
  });

  it('disconnects previous socket if start is called twice', () => {
    const { result } = renderHook(() => useMonteCarloStream());

    act(() => {
      result.current.start({ num_iterations: 50, num_voters: 200 });
    });

    const socket1 = getSocket();

    act(() => {
      result.current.start({ num_iterations: 100, num_voters: 300 });
    });

    expect(socket1.disconnect).toHaveBeenCalled();
  });
});
