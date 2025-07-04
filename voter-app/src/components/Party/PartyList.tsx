import React, {useEffect, useState} from 'react';
import { Party } from '../../types';
import { fetchAllParties } from '../../services/partiesApi';
import { Row, Col, Alert, Spinner, Card, Container } from "react-bootstrap";
import { Link } from 'react-router';

const PartyList : React.FC = () => {
    const[parties, SetParties] = useState<Party[]>([]);
    const[error, setError] = useState<string | null>(null);
    const[loading, setLoading] = useState<boolean>(true);


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
            <h1 className="text-center mb-4">Parties</h1>
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
        </Container>
    )
};

export default PartyList;