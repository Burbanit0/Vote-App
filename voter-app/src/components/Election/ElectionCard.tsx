// src/components/ElectionCard.tsx
import React from 'react';
import { Card, Row, Col } from 'react-bootstrap';
import { Election } from '../../types';
import { Link } from 'react-router-dom';
import { getElectionStatus } from '../../services/electionStatus';

interface ElectionCardProps {
  election: Election;
}

const ElectionCard: React.FC<ElectionCardProps> = ({ election }) => {
  const status = election.status;

  const getBorderVariant = () => {
    switch (status) {
      case 'Active':
        return 'primary';
      case 'Upcoming':
        return 'warning';
      case 'Completed':
        return 'sucess';
      default:
        return 'secondary';
    }
  };

  return (
    <Link to={`/elections/${election.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <Card
        style={{ width: '18rem', margin: '1rem', borderWidth: '3px' }}
        border={getBorderVariant()}
      >
        <Card.Body>
          <Row>
            <Col md={9}>
              <Card.Title>{election.name}</Card.Title>
              <Card.Text>{election.description}</Card.Text>
              <Card.Text>
                Created by: {election.created_by.first_name} {election.created_by.last_name}
              </Card.Text>
              <Card.Text>Created at: {new Date(election.created_at).toLocaleString()}</Card.Text>
              <Card.Text>Status: {election.status}</Card.Text>
            </Col>
            <Col md={3} className="d-flex align-items-center">
              {/* <span className={`badge bg-${getStatusBadgeVariant(election.status)}`}>
              {election.status.charAt(0).toUpperCase() + election.status.slice(1)}
              </span> */}
            </Col>
          </Row>
        </Card.Body>
      </Card>
    </Link>
  );
};

export default ElectionCard;
