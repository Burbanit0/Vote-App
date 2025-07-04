import { useEffect, useState } from "react";
import { Card, Container } from "react-bootstrap";
import { useParams } from "react-router";
import { Profile_ } from "../../types";
import { fetchUserProfile } from "../../services";

const UserProfile = () => {
    const { id } = useParams<{ id: string }>();
    const [profile, setProfile] = useState<Profile_ | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchProfile = async (id: number) => {
            try {
                const response = await fetchUserProfile(id);
                setProfile(response);
            } catch (error) {
                setError('Failed to fetch the user profile');
            } finally {
                setLoading(false);
            }
        };
        fetchProfile(Number(id));
    }, [id]);

    if (loading) {
        return <div>Loading...</div>;
    }

    if (error) {
        return <div>{error}</div>
    }

    return (
        <Container className="mt-5">
            <h1 className="text-center mb-4">User Profile</h1>
            <Card>
                <Card.Body>
                <Card.Title>{profile?.username}</Card.Title>
                {profile && (
                    <div>
                    <Card.Text><strong>First Name:</strong> {profile.first_name}</Card.Text>
                    <Card.Text><strong>Last Name:</strong> {profile.last_name}</Card.Text>
                    </div>
                )}
                </Card.Body>
            </Card>
            <Card className='mt-1'>
                <Card.Body>
                <Card.Title>Participation details</Card.Title>
                {profile?.participation_details && (
                    <div>
                    <Card.Text><strong>Voted at:</strong> {profile.participation_details.voter} </Card.Text>
                    <Card.Text><strong>Candidated at:</strong> {profile.participation_details.candidate} </Card.Text>
                    <Card.Text><strong>Organized:</strong> {profile.participation_details.organizer} </Card.Text>
                    </div>
                )}
                </Card.Body>
            </Card>
        </Container>
    );
};

export default UserProfile;