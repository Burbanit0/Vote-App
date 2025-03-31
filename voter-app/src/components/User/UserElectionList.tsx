import React, { useState, useEffect } from "react";
import { Election } from '../../types';
import { fetchUserElectionList } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import { Col, Container, Row } from "react-bootstrap";
import ElectionCard from "../Election/ElectionCard";

const UserElectionList: React.FC = () => {
    const { user } = useAuth();
    const[elections, setElections] = useState<Election[]>([]);
    const[loading, setLoading] = useState<boolean>(true);
    const[error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchUserElection = async () => {
          if (user?.voter) {
            try {
              const response = await fetchUserElectionList(user.voter.id);
              setElections(response);
            } catch (err) {
              setError('Failed to fetch elections.');
            } finally {
              setLoading(false);
            }
          } else {
            setLoading(false);
          }
        };
    
        fetchUserElection();
      }, [user]);
    
    if (loading) {
        return <div>Loading...</div>;
    }
    
    if (error) {
        return <div>{error}</div>
    }


    return (
        <Container>
            <h2>Elections</h2>
            <Row>
                {elections.map((election) => (
                <Col key={election.id} md={4}>
                    <ElectionCard election={election} />
                </Col>
                ))}
            </Row>
        </Container>
    )
}

export default UserElectionList;
