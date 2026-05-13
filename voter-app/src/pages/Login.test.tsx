import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from './Login';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../services/authApi';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../services/authApi', () => ({
  loginUser: jest.fn(),
}));

describe('Login', () => {
  const mockLogin = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
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
