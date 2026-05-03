import React from 'react';
import { Container, Row } from 'react-bootstrap';
import Profile from '../components/User/Profile';

const ProfilePage: React.FC = () => {
  return (
    <Container>
      <Row className="mt-4">
        <Profile />
      </Row>
    </Container>
  );
};

export default ProfilePage;
