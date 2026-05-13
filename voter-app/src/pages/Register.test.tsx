import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Register from './Register';
import { registerUser } from '../services/authApi';

jest.mock('../services/authApi', () => ({
  registerUser: jest.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  );
}

describe('Register', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders all form fields for User role', () => {
    renderPage();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Confirm password')).toBeInTheDocument();
    expect(screen.getByLabelText('Role')).toBeInTheDocument();
    expect(screen.getByLabelText('First name')).toBeInTheDocument();
    expect(screen.getByLabelText('Last name')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Register' })).toBeInTheDocument();
  });

  it('shows error when passwords do not match', async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'different' } });
    fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'Alice' } });
    fireEvent.change(screen.getByLabelText('Last name'), { target: { value: 'Smith' } });
    fireEvent.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(
        screen.getByText('Passwords do not match.')
      ).toBeInTheDocument();
    });
  });

  it('calls registerUser and navigates home on success', async () => {
    const response = { access_token: 'token', username: 'alice' };
    (registerUser as jest.Mock).mockResolvedValue(response);
    renderPage();

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'secret' } });
    fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'Alice' } });
    fireEvent.change(screen.getByLabelText('Last name'), { target: { value: 'Smith' } });
    fireEvent.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(registerUser).toHaveBeenCalledWith('alice', 'secret', 'User', 'Alice', 'Smith');
    });

    await waitFor(() => {
      expect(localStorage.getItem('user')).toBe(JSON.stringify(response));
      expect(
        screen.getByText('Registration successful! Redirecting…')
      ).toBeInTheDocument();
    });
  });

  it('shows error when duplicate username is rejected', async () => {
    (registerUser as jest.Mock).mockRejectedValue({
      response: { data: { msg: 'Username already exists' } },
    });
    renderPage();

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'existing' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'secret' } });
    fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'A' } });
    fireEvent.change(screen.getByLabelText('Last name'), { target: { value: 'B' } });
    fireEvent.click(screen.getByRole('button', { name: 'Register' }));

    await waitFor(() => {
      expect(screen.getByText('Username already exists')).toBeInTheDocument();
    });
  });
});
