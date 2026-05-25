import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Container, Spinner, Alert } from 'react-bootstrap';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:4433';

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      navigate('/login');
      return;
    }

    (async () => {
      try {
        // Phase 4.3.e: profile lives on /api/v2/users/me now (fastapi-users).
        const profileResp = await axios.get(`${API_BASE_URL}/api/v2/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const profile = profileResp.data;
        login({
          id: profile.id,
          access_token: token,
          username: profile.username,
          role: profile.role,
          created_at: '',
          user_id: profile.id,
          first_name: profile.first_name || '',
          last_name: profile.last_name || '',
        });
        navigate('/');
      } catch {
        setError('Failed to complete sign-in. Please try again.');
      }
    })();
  }, [searchParams, login, navigate]);

  if (error) {
    return (
      <Container className="mt-5 text-center">
        <Alert variant="danger">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container className="mt-5 text-center">
      <Spinner animation="border" />
      <p className="mt-3">Signing you in…</p>
    </Container>
  );
};

export default OAuthCallback;
