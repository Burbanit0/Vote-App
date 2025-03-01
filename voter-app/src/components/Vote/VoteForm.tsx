// src/components/Vote/VoteForm.tsx
import React, { useState, useEffect } from 'react';
import { castVote, fetchCandidates, fetchVoters, deleteVote } from '../../services/api';
import { Candidate, Voter, Vote } from '../../types';

interface VoteFormProps {
  votes: Vote[];
  setVotes: React.Dispatch<React.SetStateAction<Vote[]>>;
}

const VoteForm: React.FC<VoteFormProps> = ({ votes, setVotes }) => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [voters, setVoters] = useState<Voter[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);
  const [selectedVoter, setSelectedVoter] = useState<number | null>(null);
  const [voteType, setVoteType] = useState('single_choice');

  useEffect(() => {
    const loadData = async () => {
      const candidatesData = await fetchCandidates();
      const votersData = await fetchVoters();
      setCandidates(candidatesData);
      setVoters(votersData);
    };

    loadData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCandidate !== null && selectedVoter !== null) {
      const newVote = await castVote({
        candidate_id: selectedCandidate,
        voter_id: selectedVoter,
        vote_type: voteType,
        vote_id: 0,
        rank: 0,
        weight: 0,
        rating: 0
      });
      setVotes([...votes, newVote]);
    }
  };

  const handleDelete = async (voteId: number) => {
    await deleteVote(voteId);
    setVotes(votes.filter((vote) => vote.vote_id !== voteId));
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Select Candidate:</label>
          <select
            value={selectedCandidate ?? ''}
            onChange={(e) => setSelectedCandidate(Number(e.target.value))}
            required
          >
            <option value="" disabled>Select a candidate</option>
            {candidates.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.first_name} {candidate.last_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Select Voter:</label>
          <select
            value={selectedVoter ?? ''}
            onChange={(e) => setSelectedVoter(Number(e.target.value))}
            required
          >
            <option value="" disabled>Select a voter</option>
            {voters.map((voter) => (
              <option key={voter.id} value={voter.id}>
                {voter.first_name} {voter.last_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Vote Type:</label>
          <select value={voteType} onChange={(e) => setVoteType(e.target.value)}>
            <option value="single_choice">Single Choice</option>
            <option value="ordered">Ordered</option>
            <option value="weighted">Weighted</option>
            <option value="rated">Rated</option>
          </select>
        </div>
        <button type="submit">Cast Vote</button>
      </form>
      <div>
        <h3>Cast Votes</h3>
        <ul>
          {votes.map((vote) => (
            <li key={vote.vote_id}>
              Vote ID: {vote.vote_id}, Type: {vote.vote_type}
              <button onClick={() => handleDelete(vote.vote_id)}>Delete</button>
              {/* Add Update Button and Logic Here */}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default VoteForm;
