import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, Container } from 'react-bootstrap';
import { fetchCondorcetWinner } from '../../services/api';
import { Candidate } from '../../types';

const Condorcet: React.FC = () => {
    const [winner, setWinner] = useState<Candidate | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadCondorcetWinner = async () => {
            try {
                const condorcetWinner = await fetchCondorcetWinner();
                setWinner(condorcetWinner);
            } catch (error) {
                setError('Failed to fetch the Condorcet winner:');
            }
        };

        loadCondorcetWinner();
    }, []);

    return (
        <Container>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            <h2>Condorcet Winner</h2>
            <Card>
                <Card.Body>
                    <Card.Title>{winner?.id}</Card.Title>
                    <Card.Text>
                        Congratulation to {winner?.first_name} {winner?.last_name} for being the Condorcet winner!
                    </Card.Text>
                </Card.Body>
            </Card>
        </Container>
    );
};

export default Condorcet;