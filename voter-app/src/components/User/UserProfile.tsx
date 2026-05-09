import { useEffect, useState } from 'react';
import { Card, Container } from 'react-bootstrap';
import { useParams } from 'react-router';
import { Profile_ } from '../../types';
import { fetchUserProfile } from '../../services';

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
    return <div>{error}</div>;
  }

  return (
    <Container className="mt-5">
      <h1 className="text-center mb-4">User Profile</h1>
      <Card>
        <Card.Body>
          <Card.Title>{profile?.username}</Card.Title>
          {profile && (
            <div>
              <Card.Text>
                <strong>First Name:</strong> {profile.first_name}
              </Card.Text>
              <Card.Text>
                <strong>Last Name:</strong> {profile.last_name}
              </Card.Text>
            </div>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default UserProfile;
