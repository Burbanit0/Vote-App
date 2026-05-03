// ScoreVotingComparison.tsx
import React from 'react';
import { useScoreVotingResults } from './useScoreVotingResults';
import ScoreVotingVisualizations from './ScoreVotingVisualizations';

interface ScoreVotingComparisonProps {
  scores: Array<{ voter_id: number; scores: Record<string, number> }>;
  candidates: string[];
}

const ScoreVotingComparison: React.FC<ScoreVotingComparisonProps> = ({ scores, candidates }) => {
  const results = useScoreVotingResults(scores, candidates);

  return <ScoreVotingVisualizations scores={scores} candidates={candidates} results={results} />;
};

export default ScoreVotingComparison;
