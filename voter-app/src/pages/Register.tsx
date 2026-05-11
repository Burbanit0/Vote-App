import React, { useState } from 'react';
import { registerUser } from '../services/';
import { Form, Button, Container, Row, Col, Alert } from 'react-bootstrap';
import { AxiosError } from 'axios';
import { useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';

const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<'User' | 'Admin'>('User');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();

  interface ApiErrorResponse { msg: string; }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsLoading(true);

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'));
      setIsLoading(false);
      return;
    }
    try {
      const response = await registerUser(username, password, role, firstName, lastName);
      setSuccess(t('auth.registerSuccess'));
      setIsLoading(false);
      if (response) localStorage.setItem('user', JSON.stringify(response));
      setTimeout(() => navigate('/'), 1500);
    } catch (err) {
      const axiosError = err as AxiosError<ApiErrorResponse>;
      setError(axiosError.response?.data?.msg || t('auth.registerFailed'));
      setIsLoading(false);
    }
  };

  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={6} lg={4}>
          <h2 className="text-center mb-4">{t('auth.registerTitle')}</h2>
          {error && (
            <Alert variant="danger" onClose={() => setError(null)} dismissible>
              {error}
            </Alert>
          )}
          {success && <Alert variant="success">{success}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group controlId="formUsername" className="mb-3">
              <Form.Label>{t('auth.usernameLabel')}</Form.Label>
              <Form.Control type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder={t('auth.usernamePlaceholder')} required />
            </Form.Group>
            <Form.Group controlId="formPassword" className="mb-3">
              <Form.Label>{t('auth.passwordLabel')}</Form.Label>
              <Form.Control type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t('auth.passwordPlaceholder')} required />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('auth.confirmPassword')}</Form.Label>
              <Form.Control type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder={t('auth.confirmPasswordPlaceholder')} required />
            </Form.Group>
            <Form.Group controlId="formRole" className="mb-3">
              <Form.Label>{t('auth.roleLabel')}</Form.Label>
              <Form.Control as="select" value={role} onChange={(e) => setRole(e.target.value as 'User' | 'Admin')}>
                <option value="User">User</option>
                <option value="Admin">Admin</option>
              </Form.Control>
            </Form.Group>
            {role === 'User' && (
              <>
                <Form.Group controlId="formFirstName" className="mb-3">
                  <Form.Label>{t('auth.firstNameLabel')}</Form.Label>
                  <Form.Control type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder={t('auth.firstNamePlaceholder')} required />
                </Form.Group>
                <Form.Group controlId="formLastName" className="mb-3">
                  <Form.Label>{t('auth.lastNameLabel')}</Form.Label>
                  <Form.Control type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder={t('auth.lastNamePlaceholder')} required />
                </Form.Group>
              </>
            )}
            <Button variant="primary" type="submit" disabled={isLoading} className="mt-3 w-100">
              {isLoading ? (
                <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />{t('auth.registering')}</>
              ) : t('auth.registerBtn')}
            </Button>
          </Form>
        </Col>
      </Row>
    </Container>
  );
};

export default Register;
