import React, { useState } from 'react';
import { Container, Form, Button, Alert } from 'react-bootstrap';
import { createElection } from '../../services/';

const ElectionForm: React.FC = () => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createElection(name,description, startDate, endDate);
    } catch (error) {
      setError('Failed to create election.');
    }
  };

  return (
    <Container>
      <h2 className="my-4">Create Election</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit} >
        <Form.Group controlId="formElectionName">
          <Form.Label>Election Name:</Form.Label>
          <Form.Control
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Form.Group>
        <Form.Group controlId="formElectionDescription" className='mb-2'>
          <Form.Label>Description:</Form.Label>
          <Form.Control
            as="textarea"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Form.Group>
        <Button type="submit" variant="primary">
          Create Election
        </Button>
      </Form>
    </Container>
  );
};

export default ElectionForm;