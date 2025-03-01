// src/components/Voter/VoterList.tsx
import React from 'react';
import { Voter } from '../../types';
import { deleteVoter } from '../../services/api';
import { ListGroup, Button } from 'react-bootstrap';

interface VoterListProps {
  voters: Voter[];
  setVoters: React.Dispatch<React.SetStateAction<Voter[]>>;
}

const VoterList: React.FC<VoterListProps> = ({ voters, setVoters }) => {
  const handleDelete = async (voterId: number) => {
    await deleteVoter(voterId);
    setVoters(voters.filter((voter) => voter.id !== voterId));
  };

  return (
    <div>
      <h2>Voter List</h2>
      <ListGroup>
        {voters.map((voter) => (
          <ListGroup.Item key={voter.id}>
            {voter.first_name} {voter.last_name}
            <Button variant="danger" onClick={() => handleDelete(voter.id)}>Delete</Button>
            {/* Add Update Button and Logic Here */}
          </ListGroup.Item>
        ))}
      </ListGroup>
    </div>
  );
};

export default VoterList;
