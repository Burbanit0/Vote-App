// src/components/ElectionsList.tsx

import React, { useEffect, useState } from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import ElectionCard from './ElectionCard';
import { fetchElections } from '../../services/api';
import { Election } from '../../types';


const ElectionList: React.FC = () => {
  const [elections, setElections] = useState<Election[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchElection = async () => {
      try {
        const response = await fetchElections(); // Adjust the URL as needed
        setElections(response);
      } catch (err) {
        setError('Failed to fetch elections.');
      } finally {
        setLoading(false);
      }
    };

    fetchElection();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  return (
    <Container>
      <h2>Elections</h2>
      <Row>
        {elections.map((election) => (
          <Col key={election.id} md={4}>
            <ElectionCard election={election} />
          </Col>
        ))}
      </Row>
    </Container>
  );
};

export default ElectionList;