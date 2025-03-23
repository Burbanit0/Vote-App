import React from 'react';
import { Card, ListGroup } from 'react-bootstrap';

interface SimulationResultProps {
  result: { votes: any[]; condorcet_winner: any; two_round_winner:any } | null;
}

const SimulationResult: React.FC<SimulationResultProps> = ({ result }) => {
  if (!result) return null;

  return (
    <Card>
      <Card.Header as="h3">Simulation Result</Card.Header>
      <Card.Body>
        <Card.Text>
          <strong>Condorcet Winner:</strong> Candidate {result.condorcet_winner}
        </Card.Text>
        <Card.Text>
          <strong>Two Round Winner:</strong> Candidate {result.two_round_winner}
        </Card.Text>
        <Card.Text as="h4">Votes:</Card.Text>
        <ListGroup variant="flush">
          {result.votes.map( vote => (
          <ListGroup.Item>
            <Card>
                <Card.Body>
                    <Card.Title>{vote.candidate_id}</Card.Title>
                    <Card.Text>
                        Voter: {vote.voter_id}
                        Rank: {vote.rank}
                    </Card.Text>
                    </Card.Body>
                </Card>
          </ListGroup.Item>
            ))}
        </ListGroup>
      </Card.Body>
    </Card>
  );
};

export default SimulationResult;