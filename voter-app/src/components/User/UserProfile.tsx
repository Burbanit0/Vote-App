import { useEffect, useState } from 'react';
import { Card, CardBody, CardTitle } from '@/components/ui/card';
import { Container } from '@/components/ui/grid';
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
        <CardBody>
          <CardTitle>{profile?.username}</CardTitle>
          {profile && (
            <div>
              <p>
                <strong>First Name:</strong> {profile.first_name}
              </p>
              <p>
                <strong>Last Name:</strong> {profile.last_name}
              </p>
            </div>
          )}
        </CardBody>
      </Card>
    </Container>
  );
};

export default UserProfile;
