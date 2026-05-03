import React from 'react';
import { Col, Container, Row } from 'react-bootstrap';
import PartyMembers from '../components/Party/PartyElement';
import PartyDescription from '../components/Party/PartyDescription';

const PartyDetailPage: React.FC = () => {
  return (
    <Container>
      <Row className="mt-4">
        <PartyDescription />
      </Row>
      <Row className="mt-4">
        <Col>
          <PartyMembers />
        </Col>
      </Row>
    </Container>
  );
};

export default PartyDetailPage;
