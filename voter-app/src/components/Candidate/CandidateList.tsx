// src/components/Candidate/CandidateList.tsx
import React from 'react';
import { Candidate } from '../../types';
import { deleteCandidate } from '../../services/api';

interface CandidateListProps {
  candidates: Candidate[];
  setCandidates: React.Dispatch<React.SetStateAction<Candidate[]>>;
}

const CandidateList: React.FC<CandidateListProps> = ({ candidates, setCandidates }) => {
  const handleDelete = async (candidateId: number) => {
    await deleteCandidate(candidateId);
    setCandidates(candidates.filter((candidate) => candidate.id !== candidateId));
  };

  return (
    <div>
      <h2>Candidate List</h2>
      <ul>
        {candidates.map((candidate) => (
          <li key={candidate.id}>
            {candidate.first_name} {candidate.last_name}
            <button onClick={() => handleDelete(candidate.id)}>Delete</button>
            {/* Add Update Button and Logic Here */}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default CandidateList;
