// src/pages/VoterPage.tsx
import React, { useEffect, useState } from 'react';
import VoterForm from '../components/Voter/VoterForm';
import VoterList from '../components/Voter/VoterList';
import { fetchVoters } from '../services/api';
import { Voter } from '../types';

const VoterPage: React.FC = () => {
  const [voters, setVoters] = useState<Voter[]>([]);

  useEffect(() => {
    const loadVoters = async () => {
      const data = await fetchVoters();
      setVoters(data);
    };

    loadVoters();
  }, []);

  return (
    <div>
      <h1>Manage Voters</h1>
      <VoterForm setVoters={setVoters} />
      <VoterList voters={voters} setVoters={setVoters}/>
    </div>
  );
};

export default VoterPage;
