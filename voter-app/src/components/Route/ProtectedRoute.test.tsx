import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import { useAuth } from '../../stores/useAuthStore';

jest.mock('../../stores/useAuthStore', () => ({
  ...jest.requireActual('../../stores/useAuthStore'),
  useAuth: jest.fn(),
}));

const MockChild = () => <div data-testid="protected-child">Protected Content</div>;

function renderProtected(initialEntries = ['/protected']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <MockChild />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div data-testid="login-page">Login</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('redirects to /login when not authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });
    renderProtected();
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-child')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: { username: 'alice' } });
    renderProtected();
    expect(screen.getByTestId('protected-child')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });
});
