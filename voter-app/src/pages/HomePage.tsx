import React from 'react';
import { Button, Col, Container, Row } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Container className="mt-5">
      <Row className="justify-content-center text-center mb-5">
        <Col md={8}>
          <h1 className="mb-3">Voting Methods Sandbox</h1>
          <p className="lead text-muted">
            A research tool for studying how different voting methods affect election outcomes.
            Simulate elections, compare methods, and explore strategic voting effects.
          </p>
          <div className="d-flex gap-3 justify-content-center mt-4">
            <Button variant="primary" size="lg" onClick={() => navigate('/simulation')}>
              Run Simulation
            </Button>
            <Button variant="outline-primary" size="lg" onClick={() => navigate('/simulation/compare')}>
              Compare Methods
            </Button>
          </div>
        </Col>
      </Row>

      <Row className="g-4 justify-content-center">
        {[
          {
            title: '15 Voting Methods',
            text: 'Plurality, Borda, IRV, Schulze, STAR, Condorcet and more — all compared on the same population.',
          },
          {
            title: 'Strategic Voting',
            text: 'Model sincere vs. tactical voters and measure how each method resists manipulation.',
          },
          {
            title: 'Scenario Analysis',
            text: 'Compare scenarios side-by-side to demonstrate the spoiler effect and IIA violations.',
          },
        ].map(({ title, text }) => (
          <Col key={title} md={4}>
            <div className="p-4 border rounded h-100">
              <h5 className="mb-2">{title}</h5>
              <p className="text-muted small mb-0">{text}</p>
            </div>
          </Col>
        ))}
      </Row>
    </Container>
  );
};

export default HomePage;
