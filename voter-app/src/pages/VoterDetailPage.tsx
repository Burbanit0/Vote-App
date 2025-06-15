// src/components/VotersDetailPage.tsx
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Container, Row, Col, Card, Alert } from 'react-bootstrap';
import { fetchVoterById } from '../services';
import { Voter } from '../types';


const VoterDetail = () => {
    const { id } = useParams<{ id : string }>();
    const [voter, setVoter] = useState<Voter | null >(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchVoter = async (id:number) => {
            try {
                const response = await fetchVoterById(id);
                setVoter(response);
            } catch (error) {
                setError('Failed to fetch the voter.');
            } finally {
                setLoading(false);
            }
        };
        fetchVoter(Number(id));
    }, [id]);
    if(loading) {
        return <div>Loading...</div>;
    }

    return(
        <Container className='mt-4'>
        {error && <Alert variant="danger">{error}</Alert>}
        <Row>
            <Col>
            <Card className='mt-2'>
                <Card.Body>
                <Card.Title>{voter?.first_name}</Card.Title>
                <Card.Text>{voter?.last_name}</Card.Text>
                </Card.Body>
            </Card>
            </Col>
        </Row>
        </Container>
    )
}

export default VoterDetail;
