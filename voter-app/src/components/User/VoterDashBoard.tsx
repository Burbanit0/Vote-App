import React, { useState } from 'react';
import { Card, Alert, ListGroup, Button, Container, Modal } from 'react-bootstrap';
import { useParams } from 'react-router';
import { addCandidateToElection, castVote, fetchElectionById } from '../../services';
import { cancelElectionParticipation } from '../../services';
import { Election_, Participant } from '../../types';

interface VoterDashBoardProps {
  election: Election_;
  candidates: Participant[] | undefined;
}

const VoterDashBoard: React.FC<VoterDashBoardProps> = ({ election, candidates }) => {
  const { id } = useParams<{ id: string }>();
  const [role, _] = useState<string | null>('voter');
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);
  const [showVoteModal, setShowVoteModal] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hasVoted, setHasVoted] = useState(false);
  const electionId = id ? parseInt(id) : null;

  const handleVote = async () => {
    try {
      if (selectedCandidate && electionId) {
        const _ = await castVote(selectedCandidate, electionId);
      }
      setShowVoteModal(false);
      setHasVoted(true);
      setSuccess('Your vote has been cast successfully!');
    } catch (err) {
      setError('Failed to cast vote');
      console.error('Error casting vote:', err);
    }
  };

  const handleAddCandidate = async (id: number) => {
    try {
      await addCandidateToElection(id);
    } catch (error) {
      setError('Failed to add the candidate to the list.');
      fetchElectionById(id);
    }
  };

  const handleCancelParticipation = async () => {
    try {
      if (electionId) {
        await cancelElectionParticipation(electionId);
      }
      setShowCancelModal(false);
      setSuccess('You have successfully canceled your participation in this election');
      // You might want to redirect the user after canceling participation
    } catch (err) {
      setError('Failed to cancel participation');
      console.error('Error canceling participation:', err);
    }
  };

  if (!election) {
    return <div>Loading election data...</div>;
  }

  const electionStarted = new Date(election.start_date) <= new Date();
  const canCancelParticipation = !electionStarted && role && role !== 'organizer';

  return (
    <Container>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}
      {success && (
        <Alert variant="success" onClose={() => setSuccess(null)} dismissible>
          {success}
        </Alert>
      )}
      {role === 'voter' && (
        <Card className="mb-4">
          <Card.Body>
            <Card.Title>Voting</Card.Title>
            {electionStarted ? (
              hasVoted ? (
                <Alert variant="info">You have already voted in this election</Alert>
              ) : (
                <>
                  <Card.Text>Select a candidate to vote for:</Card.Text>
                  <ListGroup>
                    {candidates?.map((candidate) => (
                      <ListGroup.Item
                        key={candidate.user_id}
                        action
                        active={selectedCandidate === candidate.user_id}
                        onClick={() => setSelectedCandidate(candidate.user_id)}
                      >
                        {candidate.first_name} {candidate.last_name}
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                  <Button
                    variant="primary"
                    className="mt-3"
                    onClick={() => setShowVoteModal(true)}
                    disabled={!selectedCandidate}
                  >
                    Cast Vote
                  </Button>
                </>
              )
            ) : (
              <Alert variant="warning">Voting has not started yet</Alert>
            )}
          </Card.Body>
        </Card>
      )}
      {(role === 'candidate' || role === 'voter') && canCancelParticipation && (
        <Card className="mb-4">
          <Card.Body>
            <Card.Title>Participation</Card.Title>
            <Card.Text>You are participating in this election as a {role}.</Card.Text>
            <Button variant="danger" onClick={() => setShowCancelModal(true)}>
              Cancel Participation
            </Button>
            {role === 'voter' && electionId && (
              <Button variant="primary" onClick={() => handleAddCandidate(electionId)}>
                Become a Candidate
              </Button>
            )}
          </Card.Body>
        </Card>
      )}
      {/* Vote Confirmation Modal */}
      <Modal show={showVoteModal} onHide={() => setShowVoteModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Confirm Your Vote</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Are you sure you want to vote for{' '}
          {candidates?.find((c) => c.id === selectedCandidate)?.username}?
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowVoteModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleVote}>
            Confirm Vote
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Cancel Participation Modal */}
      <Modal show={showCancelModal} onHide={() => setShowCancelModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Cancel Participation</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Are you sure you want to cancel your participation in this election? This action cannot be
          undone.
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCancelModal(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleCancelParticipation}>
            Confirm Cancellation
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default VoterDashBoard;
