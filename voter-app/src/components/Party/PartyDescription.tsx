import React, { useEffect, useState} from "react";
import { useParams } from "react-router-dom";
import { Card } from "react-bootstrap";
import { Party } from "../../types";
import { fetchPartyById } from "../../services/partiesApi";

const PartyDescription: React.FC = () => {
    const { party_id } = useParams<{ party_id: string}>();
    const[party, setParty] = useState<Party | null>(null);
    const[error, setError] = useState<string | null>(null);
    const[loading, setLoading] = useState<boolean>(true);

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

    return (
        <Card>
            <Card.Body>
                <Card.Title>{party?.name}</Card.Title>
                <Card.Text>{party?.description}</Card.Text>
            </Card.Body>
        </Card>
    )
}

export default PartyDescription;