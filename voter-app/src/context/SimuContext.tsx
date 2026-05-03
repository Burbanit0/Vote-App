import React, { createContext, useContext, useState } from 'react';
import { CandidateSimu, VoterSimu } from '../types';

interface SimulationContextType {
  voters: VoterSimu[];
  setVoters: (voters: VoterSimu[]) => void;
  candidates: CandidateSimu[];
  setCandidates: (candidates: CandidateSimu[]) => void;
  issues: string[];
  setIssues: (issues: string[]) => void;
}

const SimulationContext = createContext<SimulationContextType>({
  voters: [],
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setVoters: () => {},
  candidates: [],
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setCandidates: () => {},
  issues: [],
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setIssues: () => {},
});

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [voters, setVoters] = useState<VoterSimu[]>([]);
  const [candidates, setCandidates] = useState<CandidateSimu[]>([]);
  const [issues, setIssues] = useState<string[]>([]);

  return (
    <SimulationContext.Provider
      value={{
        voters,
        setVoters,
        candidates,
        setCandidates,
        issues,
        setIssues,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => useContext(SimulationContext);
