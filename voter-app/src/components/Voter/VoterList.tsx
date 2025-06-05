// src/components/Voter/VoterList.tsx
import React from 'react';
import { Voter } from '../../types';
import { deleteVoter } from '../../services/api';
import { ListGroup, Button, Container, Row, Col, ButtonGroup } from 'react-bootstrap';

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
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <h2>Voter List</h2>
          <ListGroup>
            {voters.map((voter) => (
              <ListGroup.Item key={voter.id} className="d-flex justify-content-between align-items-center">
                <span>{voter.first_name} {voter.last_name}</span>
                <div>
                  <ButtonGroup>
                    <Button variant="primary" size='sm'>
                      Update
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => handleDelete(voter.id)}>
                      Delete
                    </Button>
                  </ButtonGroup>
                </div>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>
    </Container>
  );
};

export default VoterList;
