// components/profile/PartyMembership.tsx
import React, { useState, useEffect } from 'react';
import { Card, Button, Alert } from 'react-bootstrap';
import JoinPartyModal from './JoinPartyModal';
import { useAuth } from '../../context/AuthContext';
import { Party } from '../../types';
import { fetchUserParty, removeUserFromParty } from '../../services/partiesApi';


const PartyMembership: React.FC = () => {
  const { user } = useAuth();
  const [userParty, setUserParty] = useState<Party | null>(null);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUserParties = async () => {
      try {
        setLoading(true);
        const response = await fetchUserParty();
        setUserParty(response);
      } catch (err) {
        setError('Failed to fetch party memberships');
      } finally {
        setLoading(false);
      }
    };
    fetchUserParties();
  }, []);

  const handleLeaveParty = async (partyId: number) => {
    try {
      if(!user) return;
      setLoading(true);
      await removeUserFromParty(user.user_id, partyId);
      setUserParty(null);
    } catch (err) {
      setError('Failed to leave party');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mb-4">
      <Card.Body>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <Card.Title>Party Membership</Card.Title>
          {
            !userParty && (
                <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setShowJoinModal(true)}
                >
                    Join a Party
                </Button>
            )
          }
        </div>
        {error && <Alert variant="danger">{error}</Alert>}

        {loading ? (
          <div className="text-center py-4">
            <p>Loading party memberships...</p>
          </div>
        ) : userParty ? (
            <div>
                <div className="d-flex align-items-center">
                  <div>
                    <h6 className="mb-1">{userParty.name}</h6>
                    <p className="mb-0 text-muted" style={{ fontSize: '0.8rem' }}>
                      {userParty.description}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() => handleLeaveParty(userParty.id)}
                  disabled={loading}
                >
                  Leave
                </Button>
            </div>
        ) : (
          <p>You are not currently a member of any political party.</p>
        )}

        <JoinPartyModal
          show={showJoinModal}
          onHide={() => setShowJoinModal(false)}
          onPartyJoined={() => {
            fetchUserParty();
          }}
        />
      </Card.Body>
    </Card>
  );
};

export default PartyMembership;
