import React from 'react';
import { Col, Container, Row } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import ElectionList from '../components/Election/ElectionList';

const HomePage: React.FC = () => {
  return (
    <Container className="mt-5">
      <Row className="justify-content-center text-center mb-4">
        <Col>
          <h1>Welcome to the Voting System</h1>
          <p>Here are the lists of the elections ongoing</p>
        </Col>
      </Row>
      <Row>
        <ElectionList />
      </Row>
    </Container>
  );
};

export default HomePage;
