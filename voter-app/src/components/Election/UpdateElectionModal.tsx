// UpdateElectionModal.tsx
import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert } from 'react-bootstrap';
import axios from 'axios';
import { updateElection } from '../../services';
import { Election, UpdateElectionData } from '../../types';

interface UpdateElectionModalProps {
  show: boolean;
  onHide: () => void;
  election: Election | null;
  onElectionUpdated: () => void;
}

const UpdateElectionModal: React.FC<UpdateElectionModalProps> = ({
  show,
  onHide,
  election,
  onElectionUpdated,
}) => {
  const [formData, setFormData] = useState<UpdateElectionData>({
    name: '',
    description: '',
    start_date: '',
    end_date: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize form with election data when election changes
  useEffect(() => {
    if (election) {
      setFormData({
        name: election.name,
        description: election.description || '',
        start_date: election.start_date
          ? new Date(election.start_date).toISOString().slice(0, 16)
          : '',
        end_date: election.end_date ? new Date(election.end_date).toISOString().slice(0, 16) : '',
      });
    }
  }, [election]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    if (!election?.id) {
      setError('No election selected');
      setIsSubmitting(false);
      return;
    }

    try {
      // Only send fields that have changed
      const updateData: UpdateElectionData = {};
      if (formData.name !== election.name) updateData.name = formData.name;
      if (formData.description !== election.description)
        updateData.description = formData.description;
      if (formData.start_date !== election.start_date) updateData.start_date = formData.start_date;
      if (formData.end_date !== election.end_date) updateData.end_date = formData.end_date;

      // Only proceed if there are actual changes
      if (Object.keys(updateData).length === 0) {
        setError('No changes detected');
        setIsSubmitting(false);
        return;
      }

      const updatedElection = await updateElection(election.id, updateData);
      onElectionUpdated();
      onHide();
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || 'Failed to update election');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Update Election: {election?.name}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Election Name</Form.Label>
            <Form.Control
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Description</Form.Label>
            <Form.Control
              as="textarea"
              name="description"
              rows={3}
              value={formData.description}
              onChange={handleChange}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Start Date</Form.Label>
            <Form.Control
              type="datetime-local"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              required
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>End Date</Form.Label>
            <Form.Control
              type="datetime-local"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              required
            />
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" type="submit" onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span
                className="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
              Updating...
            </>
          ) : (
            'Update Election'
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default UpdateElectionModal;
