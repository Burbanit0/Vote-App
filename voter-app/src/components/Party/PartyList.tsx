import React, {useEffect, useState} from 'react';
import { Party } from '../../types';
import { fetchAllParties } from '../../services/partiesApi';
import { Row, Col, Alert, Spinner, Card, Container, Button } from "react-bootstrap";
import { Link } from 'react-router';
import CreatePartyModal from './CreatePartyModal';
import useUserPermissions from '../../hooks/useUserPermisions';

const PartyList : React.FC = () => {
    const[parties, SetParties] = useState<Party[]>([]);
    const[error, setError] = useState<string | null>(null);
    const[loading, setLoading] = useState<boolean>(true);

    const [showCreateModal, setShowCreateModal] = useState(false);
    const { is_admin } = useUserPermissions();

    useEffect(() => {
        const fetchParties = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetchAllParties();
                SetParties(response);
            } catch (error) {
                setError('Failed to fetch all the parties');
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchParties()
    }, []) 

    if (loading) {
        return (
            <Row className="justify-content-center">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                </Spinner>
            </Row>
        )
    }

    if (error) {
        return (
            <Row>
                <Col>
                    <Alert variant="danger">{error}</Alert>
                </Col>
            </Row>
        )
    }

    return (
        <Container>
            <Row className='mb-3'>
                <Col>
                    <div className="d-flex justify-content-between align-items-center">
                        <h2 className="text-center mb-4">Parties</h2>
                        {is_admin && (
                            <Button
                                variant="primary"
                                onClick={() => setShowCreateModal(true)}>
                                Create New Party
                            </Button>
                        )}
                    </div>
                </Col>
            </Row>
            

            {parties.length > 0 ? (
                parties.map((party) => (
                    <Link key={party.id} to={`/parties/${party.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                        <Card key={party.id} className='mb-3'>
                            <Card.Title>{party.name}</Card.Title>
                            <Card.Body>{party.description}</Card.Body>
                        </Card>
                    </Link>
                ))
            ) : (
                <Alert>
                    NO Party found
                </Alert>
            )}
            <CreatePartyModal
                show={showCreateModal}
                onHide={() => setShowCreateModal(false)}
                onPartyCreated={() => {
                fetchAllParties();
                }}
            />
        </Container>
    )
};

export default PartyList;