// src/pages/CandidatePage.tsx
import React, { useEffect, useState } from 'react';
import CandidateForm from '../components/Candidate/CandidateForm';
import CandidateList from '../components/Candidate/CandidateList';
import { fetchCandidates } from '../services/api';
import { Candidate } from '../types';

const CandidatePage: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  useEffect(() => {
    const loadCandidates = async () => {
      const data = await fetchCandidates();
      setCandidates(data);
    };

    loadCandidates();
  }, []);

  return (
    <div>
      <h1>Manage Candidates</h1>
      <CandidateForm setCandidates={setCandidates} />
      <CandidateList candidates={candidates} setCandidates={setCandidates}/>
    </div>
  );
};

export default CandidatePage;
