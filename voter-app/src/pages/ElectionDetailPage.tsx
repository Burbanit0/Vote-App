// src/components/ElectionDetailPage.tsx
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Container, Row, Col, Card, Button, Alert, Spinner } from 'react-bootstrap';
import { fetchElectionById, addVoterToElection, fetchParticipants, addCandidateToElection } from '../services/';
import { Election_, Participant } from '../types';
import ElectionResults from '../components/Election/ElectionResult';
import useElectionParticipation from '../hooks/useElectionParticipation';
import VoterDashBoard from '../components/User/VoterDashBoard';
import CandidateDashBoard from '../components/User/CandidateDashBoard';

const ElectionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const electionId = id ? parseInt(id) : null;
  const [election, setElection] = useState<Election_ | null>(null);
  const [participants, setParticipants] = useState<Participant[]| null>(null);
  const [electionEnded, setElectionEnded] = useState(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingP, setLoadingP] = useState<boolean | null>(true);
  const [error, setError] = useState<string | null>(null);


  const { is_participant, role, isLoading: isParticipationLoading, error: participationError } =
    useElectionParticipation(electionId);

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
    
  useEffect(() => {
    const fetchParticipant_ = async (id:number) => {
      try {
        const response = await fetchParticipants(id);
        setParticipants(response);
      } catch (error) {
        setError('Failed to fetch the participants.');
      } finally {
        setLoadingP(false);
      }
    };
    fetchParticipant_(Number(id));
  }, [id]);

  useEffect(() => {
    const checkElectionStatus = async () => {
      if(!electionId) return;
      try {
        if(election) {
          setElectionEnded(new Date(election.end_date) <= new Date());
        }
      } catch(error) {
        console.error('Error checking election status:', error);
      }
    }
  }, []);

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

  const handleAddCandidate = async(id: number) => {
    try {
      await addCandidateToElection(id)
      const response = await fetchElectionById(id);
      setElection(response);
    } catch (error) {
      setError('Failed to add the candidate to the list.')
      fetchElectionById(id);
    }
  }

  const handleVote = async (id: number) => {
    console.log("Voted");
  }

  if (loading || isParticipationLoading || loadingP) {
    return (
      <Container className="text-center mt-5">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </Container>
    );
  }

  if (error || participationError) {
    return (
      <Container className="mt-4">
        <Alert variant="danger">{error || participationError}</Alert>
      </Container>
    );
  }

  if (!election) {
    return (
      <Container className="mt-4">
        <Alert variant="info">Election not found</Alert>
      </Container>
    );
  }

  return (
    <Container className='mt-4'>
      <Row>
        <Col>
          <Card className='mt-2'>
            <Card.Body>
              <Card.Title>{election?.name}</Card.Title>
              <Card.Text>{election?.description}</Card.Text>
              <Card.Text>Created at: {election?.created_at ? new Date(election.created_at).toLocaleString() : 'N/A'}</Card.Text>
              <Card.Text>Organizer: {election?.created_by?.first_name} {election?.created_by?.last_name}</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <Row className="mt-4">
        <Col>
          <h3>Organizer:</h3>
          <ul className="list-group">
            {participants?.filter(participant => participant.role === "organizer").map(participant =>
              <Link key={participant.user_id} to={`/users/${participant.user_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <li className="list-group-item rounded mb-2 border">
                  {participant.first_name} {participant.last_name}
                </li>
              </Link>
            )}
          </ul>
        </Col>
      </Row>
      <Row className="mt-4">
        <Col>
          <h3>Candidates:</h3>
          <ul className="list-group">
            {participants?.filter(participant => participant.role === "candidate").map(participant =>
              <Link key={participant.user_id} to={`/users/${participant.user_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <li className="list-group-item rounded mb-2 border">
                  {participant.first_name} {participant.last_name}
                </li>
              </Link>
            )}
          </ul>
        </Col>
        <Col>
          <h3>Voters:</h3>
          <ul className="list-group">
            {participants?.filter(participant => participant.role === "voter").map(participant =>
              <Link key={participant.user_id} to={`/users/${participant.user_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <li className="list-group-item rounded mb-2 border">
                  {participant.first_name} {participant.last_name}
                </li>
              </Link>
            )}
          </ul>
          {error && <Alert variant="danger">{error}</Alert>}
        </Col>
      </Row>
      {electionEnded && (
        <div className="mt-4">
          <ElectionResults electionId={Number(id)} />
        </div>
      )}
      {is_participant ? (
          <div>
            <h4>Participant View</h4>
            <p>You are participating in this election as a {role}.</p>
            {/* Add participant-specific content here */}
            {role === 'candidate' && (
            <div>
                <h5>Candidate Dashboard</h5>
                <CandidateDashBoard election={election} candidates={participants?.filter(participant => participant.role === "candidate")}/>
            </div>
            )}
            {role === 'voter' && (
            <div>
                <h5>Voter Dashboard</h5>
                <VoterDashBoard election={election} candidates={participants?.filter(participant => participant.role === "candidate")}/>
            </div>
            )}
            {role === 'organizer' && (
            <div>
                <h5>Organizer Dashboard</h5>
                {/* Organizer-specific content */}
            </div>
            )}
            </div>
            ) : (
            <div>
                <h4>Non-Participant View</h4>
                <p>You are not currently participating in this election.</p>
                <Button
                    variant="primary"
                    onClick={() => handleAddVoter(Number(id))}
                >
                Join Election 
                </Button>
                <Button
                    variant="primary"
                    onClick={() => handleAddCandidate(Number(id))}
                > Join as a Candidate</Button>
            </div>
            )}
    </Container>
  );
};

export default ElectionDetail;
