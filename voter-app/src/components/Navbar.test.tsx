import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navbar from './Navbar';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useExpertMode } from '../context/ExpertModeContext';

jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../context/ThemeContext', () => ({
  useTheme: jest.fn(),
}));

jest.mock('../context/ExpertModeContext', () => ({
  useExpertMode: jest.fn(),
}));

function renderNavbar() {
  return render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>
  );
}

describe('Navbar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useTheme as jest.Mock).mockReturnValue({ theme: 'light', toggleTheme: jest.fn() });
    (useExpertMode as jest.Mock).mockReturnValue({ expertMode: false, setExpertMode: jest.fn() });
  });

  it('renders navigation links', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null, logout: jest.fn(), loading: false });
    renderNavbar();
    expect(screen.getByText('Simulator')).toBeInTheDocument();
    expect(screen.getByText('Methods')).toBeInTheDocument();
    expect(screen.getByText('Blank Vote')).toBeInTheDocument();
  });

  it('shows login and register buttons when not authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null, logout: jest.fn(), loading: false });
    renderNavbar();
    expect(screen.getByText('Log in')).toBeInTheDocument();
    expect(screen.getByText('Create account')).toBeInTheDocument();
  });

  it('shows username and logout when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { username: 'alice' },
      logout: jest.fn(),
      loading: false,
    });
    renderNavbar();
    expect(screen.getByText('👤 alice')).toBeInTheDocument();
    expect(screen.getByText('Log out')).toBeInTheDocument();
  });

  it('returns null while loading', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null, logout: jest.fn(), loading: true });
    const { container } = renderNavbar();
    expect(container.innerHTML).toBe('');
  });
});
