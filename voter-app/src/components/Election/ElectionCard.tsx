// src/components/ElectionCard.tsx
import React from 'react';
import { Card } from 'react-bootstrap';
import { Election } from '../../types';
import { Link } from 'react-router-dom';


interface ElectionCardProps {
  election: Election;
}

const ElectionCard: React.FC<ElectionCardProps> = ({ election }) => {
  return (
    <Link to={`/elections/${election.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
        <Card style={{ width: '18rem', margin: '1rem' }}>
        <Card.Body>
            <Card.Title>{election.name}</Card.Title>
            <Card.Text>{election.description}</Card.Text>
            <Card.Text>Created by: {election.created_by}</Card.Text>
            <Card.Text>Created at: {new Date(election.created_at).toLocaleString()}</Card.Text>
        </Card.Body>
        </Card>
    </Link>
  );
};

export default ElectionCard;
