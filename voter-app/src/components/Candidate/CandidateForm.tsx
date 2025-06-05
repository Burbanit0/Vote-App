// src/components/Candidate/CandidateForm.tsx
import React, { useState } from 'react';
import { createCandidate } from '../../services/api';
import { Candidate } from '../../types';
import { Button, Form, Container, Row, Col} from 'react-bootstrap';

interface CandidateFormProps {
  setCandidates: React.Dispatch<React.SetStateAction<Candidate[]>>;
}

const CandidateForm: React.FC<CandidateFormProps> = ({ setCandidates }) => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newCandidate = await createCandidate({ first_name: firstName, last_name: lastName });
    setCandidates((prevCandidates) => [...prevCandidates, newCandidate]);
    setFirstName('');
    setLastName('');
  };

  return (
    <Container className="mt-5">
    <Row className="justify-content-center">
      <Col md={6} lg={4}>
        <Form onSubmit={handleSubmit}>
          <Form.Group>
            <Form.Label>First Name</Form.Label>
            <Form.Control
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Candidate First name"
              required
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Last Name</Form.Label>
            <Form.Control
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Candidate Last name"
              required
            />
          </Form.Group>
          <Button type="submit" className="mt-3">Add Candidate</Button>
        </Form>
      </Col>
    </Row>
  </Container>
  );
};

export default CandidateForm;