// src/components/Profile.tsx

import React from 'react';
import { Card, Container, Alert } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';



const Profile: React.FC = () => {
  const { user } = useAuth();

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
          <Card.Title>{user?.username}</Card.Title>
          <Card.Text><strong>Role:</strong> {user?.role}</Card.Text>
          {user?.voter && (
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
