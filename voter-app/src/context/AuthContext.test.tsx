import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { useAuthStore } from '../stores/useAuthStore';
import { User } from '../types';

const mockUser: User = {
  id: 1,
  user_id: 1,
  username: 'testuser',
  access_token: 'abc123',
  role: 'User',
  created_at: '2025-01-01T00:00:00Z',
  first_name: 'Test',
  last_name: 'User',
};

const TestConsumer = () => {
  const { user, login, logout, loading } = useAuth();
  return (
    <div>
      <span data-testid="loading">{loading ? 'loading' : 'done'}</span>
      <span data-testid="user">{user ? user.username : 'null'}</span>
      <button data-testid="login-btn" onClick={() => login(mockUser)}>
        Login
      </button>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ user: null, loading: true });
  });

  it('renders children', () => {
    render(
      <AuthProvider>
        <div data-testid="child">child</div>
      </AuthProvider>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('starts with loading=true then resolves to false', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('loading')).toHaveTextContent('done');
  });

  it('starts with null user when localStorage is empty', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });

  it('restores user from localStorage on mount', () => {
    localStorage.setItem('user', JSON.stringify(mockUser));
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
  });

  it('sets user on login', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    fireEvent.click(screen.getByTestId('login-btn'));
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
  });

  it('persists user to localStorage on login', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    fireEvent.click(screen.getByTestId('login-btn'));
    const stored = localStorage.getItem('user');
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored!).username).toBe('testuser');
  });

  it('clears user on logout', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    fireEvent.click(screen.getByTestId('login-btn'));
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
    fireEvent.click(screen.getByTestId('logout-btn'));
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });

  it('removes user from localStorage on logout', () => {
    localStorage.setItem('user', JSON.stringify(mockUser));
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    fireEvent.click(screen.getByTestId('logout-btn'));
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('works without a provider (store-backed)', () => {
    // useAuth now reads from useAuthStore, so it no longer requires a provider.
    localStorage.setItem('user', JSON.stringify(mockUser));
    useAuthStore.getState().hydrate();
    render(<TestConsumer />);
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
  });
});
