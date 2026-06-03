import React from 'react';
import { Navigate, Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { Trans, useTranslation } from 'react-i18next';
import { useAuth } from '../../stores/useAuthStore';

const PublicBanner: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div
      style={{ backgroundColor: '#cff4fc', borderBottom: '1px solid #9eeaf9', position: 'sticky', top: 56, zIndex: 900 }}
      className="py-2 px-3 d-flex justify-content-between align-items-center flex-wrap gap-2"
    >
      <span className="small text-info-emphasis"><Trans i18nKey="auth.readOnlyBanner" /></span>
      <div className="d-flex gap-2">
        <Link to="/login">
          <Button variant="outline-info" size="sm">{t('auth.loginBtn')}</Button>
        </Link>
        <Link to="/register">
          <Button variant="info" size="sm">{t('auth.signup')}</Button>
        </Link>
      </div>
    </div>
  );
};

interface Props {
  component: React.FC;
  role?: string;
  requireAuth?: boolean;
}

const AuthGuard: React.FC<Props> = ({ component: Component, role, requireAuth = true }) => {
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  if (loading) return <div className="p-4 text-center text-muted">{t('common.loading')}</div>;

  if (!user && requireAuth) return <Navigate to="/login" />;

  if (role && user?.role !== role) return <Navigate to="/" />;

  if (!user && !requireAuth) {
    return (
      <>
        <PublicBanner />
        <Component />
      </>
    );
  }

  return <Component />;
};

export default AuthGuard;
