// src/components/Profile.tsx

import React, { useState, useEffect } from 'react';
import { Card, Container, Alert, ListGroup } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';
import { Profile_ } from '../../types';
import { fetchProfileData } from '../../services';
import profilePicture from '../../../src/assets/profile_picture/profile_picture_user3.jpg';

const Profile: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile_>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetchProfileData();
        setProfile(response);
      } catch (error) {
        setError('Failed to fetch the profile');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  if (!user) {
    return (
      <Container className="mt-5">
        <Alert variant="warning">No user data available</Alert>
      </Container>
    );
  }

  return (
    <Container className="mt-5">
      <Card>
        <Card.Body>
          <Card.Title className="text-center">{profile?.username}</Card.Title>
          {profile && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div>
                  <Card.Img src={profilePicture} style={{ maxWidth: '100px' }} />
                </div>
                <div>
                  <Card.Text>
                    <strong>First Name:</strong> {profile.first_name}
                  </Card.Text>
                  <Card.Text>
                    <strong>Last Name:</strong> {profile.last_name}
                  </Card.Text>
                </div>
              </div>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default Profile;
