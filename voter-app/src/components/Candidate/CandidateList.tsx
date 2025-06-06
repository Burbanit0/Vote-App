import React, { useState } from 'react';
import { Container, Row, Col, ListGroup, Button, ButtonGroup, Modal, Form } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import { updateCandidate } from '../../services/';

// Define the type for handleDelete
type HandleDeleteType = (id: number) => void;

interface CandidateListProps {
  candidates: { id: number; first_name: string; last_name: string }[];
  handleDelete: HandleDeleteType;
}

const CandidateList: React.FC<CandidateListProps> = ({ candidates, handleDelete }) => {
  const [showModal, setShowModal] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<{ id: number; first_name: string; last_name: string } | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const handleClose = () => setShowModal(false);
  const handleShow = (candidate: { id: number; first_name: string; last_name: string }) => {
    setSelectedCandidate(candidate);
    setFirstName(candidate.first_name);
    setLastName(candidate.last_name);
    setShowModal(true);
  };

  const handleUpdate = async () => {
    if (selectedCandidate) {
      try {
        await updateCandidate(selectedCandidate.id, { first_name: firstName, last_name: lastName })
        // Update the candidate in the local state or refetch the candidates list
        handleClose();
      } catch (error) {
        console.error('Error updating candidate:', error);
      }
    }
  };

  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <h2>Candidate List</h2>
          <ListGroup>
            {candidates.map((candidate) => (
              <ListGroup.Item key={candidate.id} className="d-flex justify-content-between align-items-center">
                <span>{candidate.first_name} {candidate.last_name}</span>
                <div>
                  <ButtonGroup>
                    <Button variant="primary" size="sm" onClick={() => handleShow(candidate)}>
                      Update
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => handleDelete(candidate.id)}>
                      Delete
                    </Button>
                  </ButtonGroup>
                </div>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Col>
      </Row>

      <Modal show={showModal} onHide={handleClose}>
        <Modal.Header closeButton>
          <Modal.Title>Update Candidate</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group>
              <Form.Label>First Name</Form.Label>
              <Form.Control
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Last Name</Form.Label>
              <Form.Control
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose}>
            Close
          </Button>
          <Button variant="primary" onClick={handleUpdate}>
            Save Changes
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default CandidateList;
