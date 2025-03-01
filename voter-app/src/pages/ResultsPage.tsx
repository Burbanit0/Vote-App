// src/pages/ResultsPage.tsx
import React, { useEffect, useState } from 'react';
import VoteResults from '../components/Vote/VoteResults';
import { fetchAllResults } from '../services/api';
import { Result } from '../types';

const ResultsPage: React.FC = () => {
  const [results, setResults] = useState<Result[]>([]);

  useEffect(() => {
    const loadResults = async () => {
      const data = await fetchAllResults();
      setResults(data);
    };

    loadResults();
  }, []);

  return (
    <div>
      <h1>Voting Results</h1>
      <VoteResults results={results} />
    </div>
  );
};

export default ResultsPage;
