import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

const HomePage: React.FC = () => {
  return (
    <Container className="mt-5">
      <Row className="justify-content-center text-center mb-4">
        <Col>
          <h1>Welcome to the Voting System</h1>
          <p>Use the navigation links to manage candidates, voters, cast votes, and view results.</p>
        </Col>
      </Row>
      <Row className="justify-content-center">
        <Col md={6} lg={3} className="mb-4">
          <Card>
            <Card.Body>
              <Card.Title>Manage Candidates</Card.Title>
              <Card.Text>Add, update, or delete candidates in the system.</Card.Text>
              <Link to="/candidates">
                <Button variant="primary" className="w-100">Go to Candidates</Button>
              </Link>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} lg={3} className="mb-4">
          <Card>
            <Card.Body>
              <Card.Title>Manage Voters</Card.Title>
              <Card.Text>Add, update, or delete voters in the system.</Card.Text>
              <Link to="/voters">
                <Button variant="primary" className="w-100">Go to Voters</Button>
              </Link>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} lg={3} className="mb-4">
          <Card>
            <Card.Body>
              <Card.Title>Cast Your Vote</Card.Title>
              <Card.Text>Vote for your preferred candidate.</Card.Text>
              <Link to="/vote">
                <Button variant="primary" className="w-100">Go to Vote</Button>
              </Link>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} lg={3} className="mb-4">
          <Card>
            <Card.Body>
              <Card.Title>View Results</Card.Title>
              <Card.Text>See the results of the election.</Card.Text>
              <Link to="/results">
                <Button variant="primary" className="w-100">Go to Results</Button>
              </Link>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default HomePage;
