import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../stores/useAuthStore';

const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:4434';

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
        // The token came in via the URL and isn't persisted yet, so we carry it
        // explicitly with a raw fetch (the apiClient middleware reads the stored
        // token, which isn't set until login() below).
        const profileResp = await fetch(`${API_BASE_URL}/api/v2/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!profileResp.ok) throw new Error('profile fetch failed');
        const profile = await profileResp.json();
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
      <div data-style="tailwind" className="mx-auto mt-12 w-full max-w-[1140px] px-3 text-center">
        <div role="alert" className="rounded-md border border-red-300 bg-red-100 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div data-style="tailwind" className="mx-auto mt-12 w-full max-w-[1140px] px-3 text-center">
      <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" aria-label="loading" />
      <p className="mt-4">Signing you in…</p>
    </div>
  );
};

export default OAuthCallback;
