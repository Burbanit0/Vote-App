// src/pages/VotePage.tsx
import React from 'react';
import VoteForm from '../components/Vote/VoteForm';
import { Container, Row, Col, Card } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

const VotePage: React.FC = () => {
  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card className="text-center">
            <Card.Header as="h1">Cast Your Vote</Card.Header>
            <Card.Body>
              <VoteForm/>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default VotePage;
