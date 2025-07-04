// src/components/Profile.tsx

import React, { useState, useEffect } from 'react';
import { Card, Container, Alert } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';
import { Profile_ } from '../../types';
import { fetchProfileData } from '../../services';


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
    return <div>{error}</div>
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
      <h1 className="text-center mb-4">User Profile</h1>
      <Card>
        <Card.Body>
          <Card.Title>{profile?.username}</Card.Title>
          {profile && (
            <div>
              <Card.Text><strong>First Name:</strong> {profile.first_name}</Card.Text>
              <Card.Text><strong>Last Name:</strong> {profile.last_name}</Card.Text>
            </div>
          )}
        </Card.Body>
      </Card>
      <Card className='mt-1'>
        <Card.Body>
          <Card.Title>Participation details</Card.Title>
          {profile?.participation_details && (
            <div>
              <Card.Text><strong>Voted at:</strong> {profile.participation_details.voter} </Card.Text>
              <Card.Text><strong>Candidated at:</strong> {profile.participation_details.candidate} </Card.Text>
              <Card.Text><strong>Organized:</strong> {profile.participation_details.organizer} </Card.Text>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default Profile;
