import React, { useState, useEffect } from 'react';
import { Form, Button, Container, Row, Col, ListGroup, Badge } from 'react-bootstrap';
import { castVote, fetchCandidates, fetchVoters, deleteVote } from '../../services/api';
import { Candidate, Voter, Vote } from '../../types';
import 'bootstrap/dist/css/bootstrap.min.css';

interface VoteFormProps {
  votes: Vote[];
  setVotes: React.Dispatch<React.SetStateAction<Vote[]>>;
  loggedInVoter?: Voter; // Pass the logged-in voter information
}

const VoteForm: React.FC<VoteFormProps> = ({ votes, setVotes, loggedInVoter }) => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [voters, setVoters] = useState<Voter[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);
  const [selectedVoter, setSelectedVoter] = useState<number | null>(null);
  const [voteType, setVoteType] = useState('single_choice');
  const [rank, setRank] = useState<number | null>(null);
  const [weight, setWeight] = useState<number | null>(null);
  const [order, setOrder] = useState<Map<number, number>>(new Map());

  useEffect(() => {
    const loadData = async () => {
      const candidatesData = await fetchCandidates();
      const votersData = await fetchVoters();
      setCandidates(candidatesData);
      setVoters(votersData);
      initializeOrder(candidatesData);
    };

    loadData();
  }, []);

  useEffect(() => {
    if (loggedInVoter) {
      setSelectedVoter(loggedInVoter.id);
    }
  }, [loggedInVoter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCandidate !== null && selectedVoter !== null) {
      const newVote = await castVote({
        candidate_id: selectedCandidate,
        voter_id: selectedVoter,
        vote_type: voteType,
        rank: rank ?? 0,
        weight: weight ?? 0,
        rating: 0,
        vote_id: 0
      });
      setVotes([...votes, newVote]);
    }
  };

  // const handleDelete = async (voteId: number) => {
  //   await deleteVote(voteId);
  //   setVotes(votes.filter((vote) => vote.vote_id !== voteId));
  // };

  const initializeOrder = (candidates: Candidate[]) => {
    const newOrder = new Map<number, number>();
    candidates.forEach((candidate, index) => {
      newOrder.set(candidate.id, index + 1);
    });
    setOrder(newOrder);
  };

  const updateOrder = (candidateId: number) => {
    const currentOrder = order.get(candidateId);
    const maxOrder = candidates.length;

    // Create a new order map
    const newOrder = new Map<number, number>();
    let newOrderValue = currentOrder !== maxOrder ? currentOrder! + 1 : 1;

    // Adjust other candidates' order if necessary
    candidates.forEach((candidate) => {
      if (candidate.id === candidateId) {
        newOrder.set(candidate.id, newOrderValue);
      } else {
        const existingOrder = order.get(candidate.id);
        if (existingOrder === newOrderValue) {
          newOrder.set(candidate.id, newOrderValue === maxOrder ? 1 : newOrderValue + 1);
        } else {
          newOrder.set(candidate.id, existingOrder!);
        }
      }
    });


    setOrder(newOrder);
    setSelectedCandidate(candidateId);
  };

  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Form onSubmit={handleSubmit}>
            <Form.Group>
              <Form.Label>Select Candidate:</Form.Label>
              <ListGroup>
                {candidates.map((candidate) => (
                  <ListGroup.Item
                  key={candidate.id}
                  active={selectedCandidate === candidate.id}
                  onClick={() => updateOrder(candidate.id)}
                  as='li'
                  className='d-flex justify-content-between align-items-start'
                  >
                  {candidate.first_name} {candidate.last_name}
                  <Badge pill>{order.get(candidate.id)}</Badge>
                </ListGroup.Item>
                ))}
              </ListGroup>
            </Form.Group>
            {!loggedInVoter && (
              <Form.Group>
                <Form.Label>Select Voter:</Form.Label>
                <Form.Control
                  as="select"
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
                </Form.Control>
              </Form.Group>
            )}
            <Form.Group>
              <Form.Label>Vote Type:</Form.Label>
              <Form.Control
                as="select"
                value={voteType}
                onChange={(e) => setVoteType(e.target.value)}
              >
                <option value="single_choice">Single Choice</option>
                <option value="ordered">Ordered</option>
                <option value="weighted">Weighted</option>
                <option value="rated">Rated</option>
              </Form.Control>
            </Form.Group>
            {voteType === 'ordered' && (
              <Form.Group>
                <Form.Label>Rank:</Form.Label>
                <Form.Control
                  type="number"
                  value={rank ?? ''}
                  onChange={(e) => setRank(Number(e.target.value))}
                />
              </Form.Group>
            )}
            {voteType === 'weighted' && (
              <Form.Group>
                <Form.Label>Weight:</Form.Label>
                <Form.Control
                  type="number"
                  step="0.1"
                  value={weight ?? ''}
                  onChange={(e) => setWeight(Number(e.target.value))}
                />
              </Form.Group>
            )}
            <Button variant="primary" type="submit" className="mt-3">
              Cast Vote
            </Button>
          </Form>
        </Col>
      </Row>
    </Container>
  );
};

export default VoteForm;
