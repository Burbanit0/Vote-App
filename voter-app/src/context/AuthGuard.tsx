import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

const AuthGuard: React.FC<{ component: React.FC; role?: 'User' | 'Admin' }> = ({
  component: Component,
  role,
}) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>; // Render a loading indicator while fetching user data
  }

  if (!user) {
    return <Navigate to="/login" />; // Redirect to login if no user is authenticated
  }

  if (role && user.role !== role) {
    return <Navigate to="/" />; // Redirect to home or another page if the role doesn't match
  }

  return <Component />;
};

export default AuthGuard;
