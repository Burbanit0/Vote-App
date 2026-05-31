import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../stores/useAuthStore';
import { googleLogin, loginUser } from '../services/';
import { Form, Button, Container, Row, Col, Alert } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:4434';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const userData = await loginUser(username, password);
      login(userData);
      navigate('/');
    } catch {
      setError(t('auth.loginFailed'));
    }
  };

  const handleGoogleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) return;
    try {
      const userData = await googleLogin(response.credential);
      login(userData);
      navigate('/');
    } catch {
      setError('Google login failed.');
    }
  };

  const hasGoogleClientId = process.env.VITE_GOOGLE_CLIENT_ID;

  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={6} lg={4}>
          <h2 className="text-center mb-4">{t('auth.loginTitle')}</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group controlId="formUsername" className="mb-3">
              <Form.Label>{t('auth.usernameLabel')}</Form.Label>
              <Form.Control
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('auth.usernamePlaceholder')}
                required
              />
            </Form.Group>
            <Form.Group controlId="formPassword" className="mb-3">
              <Form.Label>{t('auth.passwordLabel')}</Form.Label>
              <Form.Control
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
                required
              />
            </Form.Group>
            <Button variant="primary" type="submit" className="mt-3 w-100">
              {t('auth.loginBtn')}
            </Button>
          </Form>

          <div className="mt-4 mb-3 text-center text-muted small">— or —</div>

          {hasGoogleClientId && (
            <div className="d-flex justify-content-center mb-2">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError('Google login failed.')}
                size="large"
                theme="outline"
                text="signin_with"
                shape="rectangular"
                width="100%"
              />
            </div>
          )}

          <Button
            variant="dark"
            className="w-100"
            onClick={() => window.location.href = `${API_BASE_URL}/api/v2/auth/github`}
          >
            Sign in with GitHub
          </Button>

          <Button variant="link" onClick={() => navigate('/register')} className="mt-3">
            {t('auth.noAccount')}
          </Button>
        </Col>
      </Row>
    </Container>
  );
};

export default Login;
