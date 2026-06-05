import { render, screen, fireEvent } from '@testing-library/react';
import { useAuthStore, useAuth, getAuthToken } from './useAuthStore';
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

const Consumer = () => {
  const { user, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="user">{user ? user.username : 'null'}</span>
      <button data-testid="login" onClick={() => login(mockUser)}>
        login
      </button>
      <button data-testid="logout" onClick={logout}>
        logout
      </button>
    </div>
  );
};

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({ user: null, loading: false });
});

describe('useAuthStore', () => {
  it('starts with null user when localStorage is empty (after hydrate)', () => {
    useAuthStore.getState().hydrate();
    render(<Consumer />);
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });

  it('hydrate() restores the user from localStorage', () => {
    localStorage.setItem('user', JSON.stringify(mockUser));
    useAuthStore.getState().hydrate();
    render(<Consumer />);
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
  });

  it('login sets the user + persists; logout clears + removes', () => {
    render(<Consumer />);
    fireEvent.click(screen.getByTestId('login'));
    expect(screen.getByTestId('user')).toHaveTextContent('testuser');
    expect(JSON.parse(localStorage.getItem('user')!).username).toBe('testuser');
    fireEvent.click(screen.getByTestId('logout'));
    expect(screen.getByTestId('user')).toHaveTextContent('null');
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('getAuthToken returns the current token (or null)', () => {
    expect(getAuthToken()).toBeNull();
    useAuthStore.getState().login(mockUser);
    expect(getAuthToken()).toBe('abc123');
  });

  it('useAuth works without any provider (store-backed)', () => {
    render(<Consumer />);
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });
});
