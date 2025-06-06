import React, { useEffect, useState } from 'react';
import { Card, Container } from 'react-bootstrap';
import { fetchTwoRoundWinner } from '../../services/';
import { Candidate } from '../../types';

const TwoRoundWinner: React.FC = () => {
    const [winner, setWinner] = useState<Candidate | null>(null);
    const [error, setError] = useState<string | null>(null);
    
    useEffect(() => {
        const loadTwoRoundWinner = async () => {
            try {
                const twoRoundWinner = await fetchTwoRoundWinner();
                setWinner(twoRoundWinner);
            } catch (error) {
                setError('Failed to fetch the Two Round winner:');
            }
        };
    
        loadTwoRoundWinner();
    }, []);
    
    return (
        <Container>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            <h2>Two Round Winner</h2>
            <Card>
                <Card.Body>
                    <Card.Title>{winner?.id}</Card.Title>
                    <Card.Text>
                        Congratulation to {winner?.first_name} {winner?.last_name} for being the Two Round winner!
                    </Card.Text>
                </Card.Body>
            </Card>
        </Container>
    );
};

export default TwoRoundWinner;