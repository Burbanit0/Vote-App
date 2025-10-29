import React, { useEffect, useState} from "react";
import { useParams } from "react-router-dom";
import { Card, Container, Button, Row, Col, Alert } from "react-bootstrap";
import { Party } from "../../types";
import { fetchPartyById, removeUserFromParty, addUserFromParty } from "../../services/partiesApi";
import { useAuth } from '../../context/AuthContext';

const PartyDescription: React.FC = () => {

    const { user } = useAuth();
    const { party_id } = useParams<{ party_id: string}>();
    const[party, setParty] = useState<Party | null>(null);
    const[error, setError] = useState<string | null>(null);
    const[loading, setLoading] = useState<boolean>(true);
    const [success, setSuccess] = useState('');

    useEffect(() => {
        setLoading(true);
        setError(null);
        const fetchParty = async (id:number) => {
            try {
                const response = await fetchPartyById(id);
                setParty(response);
            } catch(error) {
                setError('Failed to fetch the party');
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchParty(Number(party_id))
    }, [party_id]);

    if (loading) {
        return <div>Loading...</div>;
    }

    if (error) {
        return <div>{error}</div>
    }

    const handleLeaveParty = async (partyId: number) => {
        try {
            if(!user) return;
            setLoading(true);
            await removeUserFromParty(user.user_id, partyId);
        } catch (err) {
          setError('Failed to leave party');
        } finally {
          setLoading(false);
        }
    };

    const handleJoinParty = async () => {
        if(!user || !party_id) return;
        try {
            if (!party) return;
            setLoading(true);
            setError('');
            setSuccess('');
            const response = await addUserFromParty(user.user_id, party.id);
            setSuccess(response.data.message);

        } catch (err) {
            setError('Failed to join the party')
        } finally {
            setLoading(false);
        }
    }

    return (
        <Container>
            <Row className="mt-4">
                <Card>
                    <Card.Body>
                        <Card.Title>{party?.name}</Card.Title>
                        <Card.Text>{party?.description}</Card.Text>
                    </Card.Body>
                </Card>
            </Row>
            <Row className="mt-4">
                <Col>
                <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleJoinParty()}
                    disabled={loading}
                >
                    Join the party
                </Button>
                </Col>
                <Col>
                    {party ? (
                        <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() => handleLeaveParty(party.id)}
                        disabled={loading}
                        >
                            Leave
                        </Button>
                    ): (
                        <Alert>Not in the Party</Alert>
                    )}
                </Col>
            </Row>
        </Container>
    )
}

export default PartyDescription;