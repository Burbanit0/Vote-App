import React from 'react';
import { Col, Container, Row } from 'react-bootstrap';
import Profile from '../components/User/Profile';
import UserElectionList from '../components/User/UserElectionList';
import ParticipationPoints from '../components/User/ParticipationPoints';

const ProfilePage: React.FC = () => {
  return (
    <Container>
      <Row className="mt-4">
        <Profile />
      </Row>
      <Row className="mt-4">
        <ParticipationPoints />
      </Row>
      <Row className="mt-4">
        <Col>
          <UserElectionList />
        </Col>
      </Row>
    </Container>
  );
};

export default ProfilePage;
