// src/components/ElectionDetailPage.tsx
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Container, Row, Col, Card, Alert } from 'react-bootstrap';
import { fetchCandidateById } from '../services/';
import { Candidate } from '../types';

const CandidateDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCandidate = async (id:number) => {
        try {
            const response = await fetchCandidateById(id);
            setCandidate(response);
        } catch (error) {
            setError('Failed to fetch the election.');
        } finally {
            setLoading(false);
        }
        };
        fetchCandidate(Number(id));
    }, [id]);
  if (loading) {
    return <div>Loading...</div>;
  }


  return (
    <Container>
      {error && <Alert variant="danger">{error}</Alert>}
      <Row>
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>{candidate?.first_name}</Card.Title>
              <Card.Text>{candidate?.last_name}</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default CandidateDetail;
