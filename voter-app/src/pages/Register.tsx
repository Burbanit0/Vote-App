import React, { useState } from 'react';
import { registerUser } from '../services/';
import { useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// ── Tailwind-migrated (Phase 6) — off react-bootstrap → shadcn Button/Input/Label.

const selectClasses =
  'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

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
      const msg = (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg;
      setError(msg || t('auth.registerFailed'));
      setIsLoading(false);
    }
  };

  return (
    <div data-style="tailwind" className="mx-auto mt-12 w-full max-w-sm px-4">
      <h2 className="mb-6 text-center text-2xl font-semibold">{t('auth.registerTitle')}</h2>

      {error && (
        <div
          role="alert"
          className="mb-4 flex items-start justify-between gap-2 rounded-md border border-border border-red-300 bg-red-100 px-3 py-2 text-sm text-red-800"
        >
          <span>{error}</span>
          <button type="button" aria-label="Close" onClick={() => setError(null)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      {success && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-border border-green-300 bg-green-100 px-3 py-2 text-sm text-green-800"
        >
          {success}
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
        <div className="space-y-1.5">
          <Label htmlFor="formConfirm">{t('auth.confirmPassword')}</Label>
          <Input
            id="formConfirm"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t('auth.confirmPasswordPlaceholder')}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="formRole">{t('auth.roleLabel')}</Label>
          <select
            id="formRole"
            className={selectClasses}
            value={role}
            onChange={(e) => setRole(e.target.value as 'User' | 'Admin')}
          >
            <option value="User">User</option>
            <option value="Admin">Admin</option>
          </select>
        </div>
        {role === 'User' && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="formFirstName">{t('auth.firstNameLabel')}</Label>
              <Input
                id="formFirstName"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder={t('auth.firstNamePlaceholder')}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="formLastName">{t('auth.lastNameLabel')}</Label>
              <Input
                id="formLastName"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder={t('auth.lastNamePlaceholder')}
                required
              />
            </div>
          </>
        )}
        <Button type="submit" disabled={isLoading} className="mt-4 w-full">
          {isLoading ? (
            <>
              <Loader2 className="mr-2 inline h-4 w-4 animate-spin" aria-hidden="true" />
              {t('auth.registering')}
            </>
          ) : (
            t('auth.registerBtn')
          )}
        </Button>
      </form>
    </div>
  );
};

export default Register;
