// src/components/Voter/VoterForm.tsx
import React, { useState } from 'react';
import { createVoter } from '../../services/';
import { Voter } from '../../types';
import { Button, Form, Container, Row, Col} from 'react-bootstrap';

interface VoterFormProps {
  setVoters: React.Dispatch<React.SetStateAction<Voter[]>>;
}

const VoterForm: React.FC<VoterFormProps> = ({ setVoters }) => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newVoter = await createVoter({ first_name: firstName, last_name:lastName });
    setVoters((prevVoters) => [...prevVoters, newVoter]);
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
                placeholder="Voter First name"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Last Name</Form.Label>
              <Form.Control
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Voter Last name"
                required
              />
            </Form.Group>
            <Button type="submit" className="mt-3">Add Voter</Button>
          </Form>
        </Col>
      </Row>
    </Container>
  );
};

export default VoterForm;
