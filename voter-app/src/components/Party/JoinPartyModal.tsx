// components/party/JoinPartyModal.tsx
import React, { useState, useEffect } from 'react';
import { Modal, Button, ListGroup, Spinner, Alert } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';
import { addUserFromParty, fetchAllParties } from '../../services/partiesApi';
import { Party } from '../../types';


interface JoinPartyModalProps {
  show: boolean;
  onHide: () => void;
  onPartyJoined: () => void;
}

const JoinPartyModal: React.FC<JoinPartyModalProps> = ({ show, onHide, onPartyJoined }) => {
  const { user } = useAuth();
  const [parties, setParties] = useState<Party[]>([]);
  const [selectedParty, setSelectedParty] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchParties = async () => {
      try {
        setLoading(true);
        const response = await fetchAllParties();
        setParties(response);
      } catch (err) {
        setError('Failed to fetch parties');
      } finally {
        setLoading(false);
      }
    };

    if (show) {
      fetchParties();
    }
  }, [show]);

  const handleJoinParty = async () => {
    if (!selectedParty || !user) return;

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const response = await addUserFromParty(user.user_id, selectedParty);
      setSuccess(response.data.message);
      onPartyJoined();
      setTimeout(() => {
        onHide();
        setSuccess('');
      }, 2000);
    } catch (err) {
      setError('Failed to join party');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <Modal.Title>Join a Political Party</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        {loading ? (
          <div className="text-center py-4">
            <Spinner animation="border" role="status">
              <span className="visually-hidden">Loading...</span>
            </Spinner>
          </div>
        ) : (
          <>
            <p>Select a political party to join:</p>
            <ListGroup className="mb-3">
              {parties.map(party => (
                <ListGroup.Item
                  key={party.id}
                  action
                  active={selectedParty === party.id}
                  onClick={() => setSelectedParty(party.id)}
                >
                  <div className="d-flex align-items-center">
                    <div>
                      <h5 className="mb-1">{party.name}</h5>
                      <p className="mb-0 text-muted" style={{ fontSize: '0.8rem' }}>
                        {party.description}
                      </p>
                    </div>
                  </div>
                </ListGroup.Item>
              ))}
            </ListGroup>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
        <Button
          variant="primary"
          onClick={handleJoinParty}
          disabled={!selectedParty || loading}
        >
          {loading ? (
            <>
              <Spinner
                as="span"
                animation="border"
                size="sm"
                role="status"
                aria-hidden="true"
                className="me-2"
              />
              Joining...
            </>
          ) : (
            'Join Party'
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default JoinPartyModal;
