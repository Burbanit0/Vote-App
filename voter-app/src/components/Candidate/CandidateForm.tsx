// src/components/Candidate/CandidateForm.tsx
import React, { useState } from 'react';
import { createCandidate } from '../../services/api';
import { Candidate } from '../../types';

interface CandidateFormProps {
  setCandidates: React.Dispatch<React.SetStateAction<Candidate[]>>;
}

const CandidateForm: React.FC<CandidateFormProps> = ({ setCandidates }) => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newCandidate = await createCandidate({ first_name: firstName, last_name: lastName });
    setCandidates((prevCandidates) => [...prevCandidates, newCandidate]);
    setFirstName('');
    setLastName('');
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
        placeholder="First Name"
        required
      />
      <input
        type="text"
        value={lastName}
        onChange={(e) => setLastName(e.target.value)}
        placeholder="Last Name"
        required
      />
      <button type="submit">Add Candidate</button>
    </form>
  );
};

export default CandidateForm;