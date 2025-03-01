// src/pages/VotePage.tsx
import React, { useState } from 'react';
import VoteForm from '../components/Vote/VoteForm';
import {Vote} from '../types';

const VotePage: React.FC = () => {
  const [votes, setVotes] = useState<Vote[]>([])
  return (
    <div>
      <h1>Cast Your Vote</h1>
      <VoteForm votes={votes} setVotes={setVotes}/>
    </div>
  );
};

export default VotePage;
