// src/components/Profile.tsx

import React, { useState, useEffect } from 'react';
import { Alert } from '@/components/ui/alert';
import { Card, CardBody, CardTitle } from '@/components/ui/card';
import { Container } from '@/components/ui/grid';
import { useAuth } from '../../stores/useAuthStore';
import { Profile_ } from '../../types';
import { fetchProfileData } from '../../services';
import profilePicture from '../../../src/assets/profile_picture/profile_picture_user3.jpg';

const Profile: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile_>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetchProfileData();
        setProfile(response);
      } catch (error) {
        setError('Failed to fetch the profile');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  if (!user) {
    return (
      <Container className="mt-5">
        <Alert variant="warning">No user data available</Alert>
      </Container>
    );
  }

  return (
    <Container className="mt-5">
      <Card>
        <CardBody>
          <CardTitle className="text-center">{profile?.username}</CardTitle>
          {profile && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div>
                  <img className="rounded-t-xl" src={profilePicture} style={{ maxWidth: '100px' }} />
                </div>
                <div>
                  <p>
                    <strong>First Name:</strong> {profile.first_name}
                  </p>
                  <p>
                    <strong>Last Name:</strong> {profile.last_name}
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </Container>
  );
};

export default Profile;
