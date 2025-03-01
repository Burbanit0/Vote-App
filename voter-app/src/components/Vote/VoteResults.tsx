// src/components/Vote/VoteResults.tsx
import React from 'react';
import { Result } from '../../types';

interface VoteResultsProps {
  results: Result[];
}

const VoteResults: React.FC<VoteResultsProps> = ({ results }) => {
  return (
    <div>
      <h2>Voting Results</h2>
      <ul>
        {results.map((result, index) => (
          <li key={index}>
            Candidate {result.candidate_id} /{result.vote_type}: {result.vote_count} votes
          </li>
        ))}
      </ul>
    </div>
  );
};

export default VoteResults;
