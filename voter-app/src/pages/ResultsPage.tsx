// src/pages/ResultsPage.tsx
import React, { useEffect, useState } from 'react';
import VoteResults from '../components/Vote/VoteResults';
import { fetchAllResults } from '../services/api';
import { Result } from '../types';
import { Card, Col, Container, Row } from 'react-bootstrap';

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
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card className="text-center">
            <Card.Header as="h1">Voting Results</Card.Header>
            <Card.Body>
              <VoteResults results={results} />
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ResultsPage;
