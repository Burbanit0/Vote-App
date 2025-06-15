// src/components/ElectionDetailPage.tsx
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Container, Row, Col, Card, Button, Alert } from 'react-bootstrap';
import { fetchElectionById, addVoterToElection } from '../services/';
import { Election_ } from '../types';

const ElectionDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [election, setElection] = useState<Election_ | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchElection_ = async (id:number) => {
        try {
            const response = await fetchElectionById(id);
            setElection(response);
        } catch (error) {
            setError('Failed to fetch the election.');
        } finally {
            setLoading(false);
        }
        };
        fetchElection_(Number(id));
    }, [id]);
    
  const handleAddVoter = async (id:number) => {
    try {
      await addVoterToElection(id)
      const response = await fetchElectionById(id);
      setElection(response);
    } catch (error) {
      setError('Failed to add the voter to the list.')
      fetchElectionById(id);
    }
 }
  if (loading) {
    return <div>Loading...</div>;
  }


  return (
    <Container>
      <Row>
        <Col>
          <Card>
            <Card.Body>
              <Card.Title>{election?.name}</Card.Title>
              <Card.Text>{election?.description}</Card.Text>
              <Card.Text>Created by: {election?.created_by}</Card.Text>
              <Card.Text>Created at: {election?.created_at ? new Date(election.created_at).toLocaleString() : 'N/A'}</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <Row className="mt-4">
        <Col>
          <h3>Candidates:</h3>
          <ul className="list-group">
            {election?.candidates?.map(candidate => (
              <Link to={`/candidates/${candidate.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <li key={candidate.id} className="list-group-item">
                  {candidate.first_name} {candidate.last_name}
                </li>
              </Link>
            ))}
          </ul>
        </Col>
        <Col>
          <h3>Voters:</h3>
          <ul className="list-group">
            {election?.voters?.map(voter => (
              <Link to={`/voters/${voter.id}`} style={{ textDecoration: 'none', color: 'inherit'}}>
                <li key={voter.id} className="list-group-item">
                  {voter.username}
                </li>
              </Link>
            ))}
          </ul>
          {error && <Alert variant="danger">{error}</Alert>}
          <Button onClick={() => handleAddVoter(Number(id))}>
            Add Me as a Voter
          </Button>
        </Col>
      </Row>
    </Container>
  );
};

export default ElectionDetail;
