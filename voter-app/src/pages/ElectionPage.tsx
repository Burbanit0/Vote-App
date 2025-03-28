// src/pages/ElectionPage.tsx
import React from 'react';
import ElectionForm from '../components/Election/ElectionForm';
import { Container, Row, Col, Card } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import ElectionList from '../components/Election/ElectionList';

const ElectionPage: React.FC = () => {
  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card className="text-center">
            <Card.Header as="h1">Cast Your Vote</Card.Header>
            <Card.Body>
              <ElectionForm/>
            </Card.Body>
          </Card>
        </Col>
        <ElectionList/>
      </Row>
    </Container>
  );
};

export default ElectionPage;