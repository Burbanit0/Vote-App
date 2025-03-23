// src/components/Vote/VoteResults.tsx
import React from 'react';
import { Result } from '../../types';
import { Card, Col, Container, Row } from 'react-bootstrap';

interface VoteResultsProps {
  results: Result[];
}

const VoteResults: React.FC<VoteResultsProps> = ({ results }) => {
  return (
      <Container>
      <Row>
        {results.map(result => (
          <Col key={result.candidate_id} md={4} className="mb-4">
            <Card>
              <Card.Img variant="top" src={`../profil_picture.png`} />
              <Card.Body>
                <Card.Title>{result.candidate_id}</Card.Title>
                <Card.Text>
                  Vote Type: {result.vote_type}<br />
                  Votes: {result.vote_count}
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    </Container>
  );
};

export default VoteResults;