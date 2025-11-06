import React, { useState, useEffect } from 'react';
import { Table, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';
import { User } from '../../types';
import { fetchMembers } from '../../services/partiesApi';
import { useParams } from 'react-router';

const PartyMembers: React.FC = () => {
  const { party_id } = useParams<{ party_id: string}>();
  const [members, setMembers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAllMembers = async (party_id: number) => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchMembers(party_id);
        setMembers(response);
      } catch (err) {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.message || 'Failed to fetch party members');
        } else {
          setError('An unexpected error occurred');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllMembers(Number(party_id));
  }, [party_id]);

  return (
    <div className="mt-4">
      <h3>Party Members</h3>

      {error && <Alert variant="danger">{error}</Alert>}

      {isLoading ? (
        <div className="text-center">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </div>
      ) : (
        <Table striped bordered hover>
          <thead>
            <tr>
              <th>Username</th>
              <th>Name</th>
            </tr>
          </thead>
          <tbody>
            {members.length > 0 ? (
              members.map(member => (
                <tr key={member.id}>
                  <td>{member.username}</td>
                  <td>{member.first_name} {member.last_name}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="text-center">No members found</td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  );
};

export default PartyMembers;
