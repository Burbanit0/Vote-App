import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../stores/useAuthStore';
import { googleLogin, loginUser } from '../services/';
import { useTranslation } from 'react-i18next';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// ── Tailwind-migrated (Phase 6) — off react-bootstrap → shadcn Button/Input/Label.
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
    <div data-style="tailwind" className="mx-auto mt-12 w-full max-w-sm px-4">
      <h2 className="mb-6 text-center text-2xl font-semibold">{t('auth.loginTitle')}</h2>

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-border border-red-300 bg-red-100 px-3 py-2 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="formUsername">{t('auth.usernameLabel')}</Label>
          <Input
            id="formUsername"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t('auth.usernamePlaceholder')}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="formPassword">{t('auth.passwordLabel')}</Label>
          <Input
            id="formPassword"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('auth.passwordPlaceholder')}
            required
          />
        </div>
        <Button type="submit" className="mt-4 w-full">
          {t('auth.loginBtn')}
        </Button>
      </form>

      <div className="mb-4 mt-6 text-center text-sm text-muted-foreground">— or —</div>

      {hasGoogleClientId && (
        <div className="mb-2 flex justify-center">
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
        className="w-full bg-slate-900 text-white hover:bg-slate-900/90"
        onClick={() => (window.location.href = `${API_BASE_URL}/api/v2/auth/github`)}
      >
        Sign in with GitHub
      </Button>

      <Button variant="link" onClick={() => navigate('/register')} className="mt-4">
        {t('auth.noAccount')}
      </Button>
    </div>
  );
};

export default Login;
