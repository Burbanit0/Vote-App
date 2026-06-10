import { useCallback, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

// Phase 4.4: Monte Carlo streaming lives on the FastAPI ASGI app at
// /api/v2/socket.io. The default points at the local FastAPI dev port
// (4434); VITE_SOCKET_URL overrides for prod where it'll be the Caddy
// fronted origin.
const SOCKET_URL = process.env.VITE_SOCKET_URL || 'http://localhost:4434';
const SOCKET_PATH = '/api/v2/socket.io';

export interface MethodStreamStats {
  winner_distribution: Record<string, number>;
  most_common_winner: string | null;
}

export interface StreamProgress {
  iteration: number;
  total: number;
  partial_results: Record<string, MethodStreamStats>;
  condorcet_exists_rate: number;
  // Convergence fields
  regret_history: Record<string, number[]>;
  agreement_rate: number;
  regret_ci_half: Record<string, number | null>;
  iteration_checkpoints: number[];
}

export interface StreamComplete {
  final_results: Record<string, MethodStreamStats>;
  num_iterations: number;
  num_voters: number;
  condorcet_exists_rate: number;
}

export interface MonteCarloStreamParams {
  num_iterations: number;
  num_voters: number;
  num_candidates?: number;
  candidates?: string[];
  ideology?: string;
}

interface State {
  progress: number;
  iteration: number;
  total: number;
  partialResults: Record<string, MethodStreamStats>;
  condorcetRate: number;
  isRunning: boolean;
  complete: StreamComplete | null;
  error: string | null;
  // Convergence state
  regretHistory: Record<string, number[]>;
  agreementHistory: number[];
  ciHalfLatest: Record<string, number | null>;
  iterationCheckpoints: number[];
}

const INITIAL: State = {
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
};

export function useMonteCarloStream() {
  const socketRef = useRef<Socket | null>(null);
  const [state, setState] = useState<State>(INITIAL);

  const stop = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.emit('stop_monte_carlo', {});
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setState((s) => ({ ...s, isRunning: false }));
  }, []);

  const start = useCallback((params: MonteCarloStreamParams) => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    setState({ ...INITIAL, isRunning: true, total: params.num_iterations });

    const socket = io(SOCKET_URL, {
      path: SOCKET_PATH,
      transports: ['websocket', 'polling'],
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('start_monte_carlo', params);
    });

    socket.on('monte_carlo_progress', (data: StreamProgress) => {
      setState((s) => ({
        ...s,
        iteration: data.iteration,
        total: data.total,
        progress: Math.round((data.iteration / data.total) * 100),
        partialResults: data.partial_results,
        condorcetRate: data.condorcet_exists_rate,
        // Convergence: backend sends full accumulated history each time
        regretHistory: data.regret_history ?? s.regretHistory,
        agreementHistory: [...s.agreementHistory, data.agreement_rate ?? 0],
        ciHalfLatest: data.regret_ci_half ?? s.ciHalfLatest,
        iterationCheckpoints: data.iteration_checkpoints ?? s.iterationCheckpoints,
      }));
    });

    socket.on('monte_carlo_complete', (data: StreamComplete) => {
      setState((s) => ({
        ...s,
        isRunning: false,
        progress: 100,
        complete: data,
        condorcetRate: data.condorcet_exists_rate,
      }));
      socket.disconnect();
      socketRef.current = null;
    });

    socket.on('monte_carlo_error', (data: { message: string }) => {
      setState((s) => ({ ...s, isRunning: false, error: data.message }));
      socket.disconnect();
      socketRef.current = null;
    });

    socket.on('connect_error', () => {
      setState((s) => ({ ...s, isRunning: false, error: 'WebSocket connection failed' }));
      socketRef.current = null;
    });
  }, []);

  const reset = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    setState(INITIAL);
  }, []);

  return { ...state, start, stop, reset };
}
