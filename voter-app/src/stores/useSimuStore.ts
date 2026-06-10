/**
 * useSimuStore — Simulation-form working set (Phase 5.5).
 *
 * Ephemeral voters/candidates/issues used by the older Simulation-form
 * visualizations (CandidatesVisualization / UtilityVisualization /
 * VoterVisualization). Former SimuContext; `useSimulation()` is the convenience
 * hook those consumers use. Not persisted (was never persisted as a context).
 */
import { create } from 'zustand';
import { CandidateSimu, VoterSimu } from '../types';

interface SimuState {
  voters: VoterSimu[];
  setVoters: (voters: VoterSimu[]) => void;
  candidates: CandidateSimu[];
  setCandidates: (candidates: CandidateSimu[]) => void;
  issues: string[];
  setIssues: (issues: string[]) => void;
}

export const useSimuStore = create<SimuState>((set) => ({
  voters: [],
  setVoters: (voters) => set({ voters }),
  candidates: [],
  setCandidates: (candidates) => set({ candidates }),
  issues: [],
  setIssues: (issues) => set({ issues }),
}));

// Convenience hook (former SimuContext API). Select fields individually.
export function useSimulation() {
  const voters = useSimuStore((s) => s.voters);
  const setVoters = useSimuStore((s) => s.setVoters);
  const candidates = useSimuStore((s) => s.candidates);
  const setCandidates = useSimuStore((s) => s.setCandidates);
  const issues = useSimuStore((s) => s.issues);
  const setIssues = useSimuStore((s) => s.setIssues);
  return { voters, setVoters, candidates, setCandidates, issues, setIssues };
}
