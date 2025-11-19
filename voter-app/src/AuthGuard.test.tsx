import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AuthGuard from './context/AuthGuard';
import { useAuth } from './context/AuthContext';

jest.mock('./context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

const MockComponent = () => <div data-testid="mock-component">Mock Component</div>;

describe('AuthGuard', () => {
  const mockUseAuth = useAuth as jest.Mock;

  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: null });
  });

  it('redirects to /login when not authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/protected" element={<AuthGuard component={MockComponent} />} />
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('renders the component when authenticated', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/protected" element={<AuthGuard component={MockComponent} />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId('mock-component')).toBeInTheDocument();
  });
});
