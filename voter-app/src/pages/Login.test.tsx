import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from './Login';
import { useAuth } from '../stores/useAuthStore';
import { loginUser } from '../services/authApi';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual('react-router-dom')),
  useNavigate: () => mockNavigate,
}));

vi.mock('../stores/useAuthStore', async () => ({
  ...(await vi.importActual('../stores/useAuthStore')),
  useAuth: vi.fn(),
}));

vi.mock('../services/authApi', () => ({
  loginUser: vi.fn(),
  googleLogin: vi.fn(),
}));

vi.mock('@react-oauth/google', () => ({
  GoogleLogin: ({ onSuccess }: { onSuccess: (resp: { credential: string }) => void }) => (
    <button
      data-testid="google-login-btn"
      onClick={() => onSuccess({ credential: 'mock-credential' })}
    >
      Google
    </button>
  ),
}));

describe('Login', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    process.env.VITE_GOOGLE_CLIENT_ID = 'test-client-id';
    (useAuth as jest.Mock).mockReturnValue({ login: mockLogin, user: null });
  });

  it('renders username field, password field, and submit button', () => {
    render(<Login />);
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Log in' })).toBeInTheDocument();
  });

  it('calls loginUser with entered credentials on submit', async () => {
    (loginUser as jest.Mock).mockResolvedValue({ access_token: 'token' });
    render(<Login />);

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

    await waitFor(() => {
      expect(loginUser).toHaveBeenCalledWith('alice', 'secret');
    });
  });

  it('displays error message when login fails', async () => {
    (loginUser as jest.Mock).mockRejectedValue(new Error('Invalid credentials'));
    render(<Login />);

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

    await waitFor(() => {
      expect(
        screen.getByText('Login failed. Please check your credentials.')
      ).toBeInTheDocument();
    });
  });

  it('calls login and navigates to home on success', async () => {
    const userData = { access_token: 'token', username: 'alice' };
    (loginUser as jest.Mock).mockResolvedValue(userData);
    render(<Login />);

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(userData);
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });
});
