// src/components/Profile.tsx

import React, { useEffect, useState } from 'react';
import { fetchProfileData } from '../../services/api';
import { Card, Container, Spinner, Alert } from 'react-bootstrap';

interface Voter {
  first_name: string;
  last_name: string;
}

interface User {
  id: number;
  username: string;
  role: string;
  created_at: string;
  voter?: Voter;
}

const Profile: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const userData = await fetchProfileData();
        setUser(userData);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  if (loading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="mt-5">
        <Alert variant="danger">{error}</Alert>
      </Container>
    );
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
          <Card.Title>{user.username}</Card.Title>
          <Card.Text><strong>Role:</strong> {user.role}</Card.Text>
          <Card.Text><strong>Created At:</strong> {new Date(user.created_at).toLocaleString()}</Card.Text>
          {user.voter && (
            <div>
              <Card.Text><strong>First Name:</strong> {user.voter.first_name}</Card.Text>
              <Card.Text><strong>Last Name:</strong> {user.voter.last_name}</Card.Text>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default Profile;
