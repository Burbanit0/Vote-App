// components/dashboard/OrganizerDashboard.tsx
import React from 'react';
import { Card, Row, Col, ProgressBar, ListGroup } from 'react-bootstrap';
import { Link } from 'react-router-dom';

interface OrganizerDashboardProps {
  data: {
    role: string;
    election: {
      id: number;
      name: string;
      description: string;
      start_date: string;
      end_date: string;
      voting_method: string;
    };
    statistics: {
      voter_count: number;
      candidate_count: number;
      votes_cast: number;
      voter_participation_rate: number;
    };
  };
}

const OrganizerDashboardBis: React.FC<OrganizerDashboardProps> = ({ data }) => {
  const { election, statistics } = data;

  return (
    <div className="container mt-4">
      <h2>{election.name} Dashboard</h2>
      <p className="text-muted">{election.description}</p>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>Election Details</Card.Title>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <strong>Voting Method:</strong> {election.voting_method}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Start Date:</strong> {new Date(election.start_date).toLocaleString()}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>End Date:</strong> {new Date(election.end_date).toLocaleString()}
                </ListGroup.Item>
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>Quick Actions</Card.Title>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <Link to={`/elections/${election.id}/edit`} className="btn btn-primary w-100">
                    Edit Election
                  </Link>
                </ListGroup.Item>
                <ListGroup.Item>
                  <Link to={`/elections/${election.id}/candidates`} className="btn btn-secondary w-100">
                    Manage Candidates
                  </Link>
                </ListGroup.Item>
                <ListGroup.Item>
                  <Link to={`/elections/${election.id}/voters`} className="btn btn-secondary w-100">
                    Manage Voters
                  </Link>
                </ListGroup.Item>
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>Participation Statistics</Card.Title>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <strong>Total Voters:</strong> {statistics.voter_count}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Total Candidates:</strong> {statistics.candidate_count}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Votes Cast:</strong> {statistics.votes_cast}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Participation Rate:</strong> {statistics.voter_participation_rate}%
                  <ProgressBar
                    now={statistics.voter_participation_rate}
                    label={`${statistics.voter_participation_rate}%`}
                    max={100}
                    className="mt-2"
                  />
                </ListGroup.Item>
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card>
            <Card.Body>
              <Card.Title>Election Status</Card.Title>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <strong>Status:</strong>
                  {new Date() < new Date(election.start_date) ? (
                    <span className="badge bg-warning text-dark"> Upcoming</span>
                  ) : new Date() > new Date(election.end_date) ? (
                    <span className="badge bg-secondary"> Completed</span>
                  ) : (
                    <span className="badge bg-success"> Active</span>
                  )}
                </ListGroup.Item>
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default OrganizerDashboardBis;
