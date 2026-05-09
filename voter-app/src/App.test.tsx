import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import { useAuth } from './context/AuthContext';

// Mock all child pages and shared components
jest.mock('./components/Navbar', () => () => <div data-testid="navbar">Navbar</div>);
jest.mock(
  './components/Route/ErrorBoundary',
  () =>
    ({ children }: { children: React.ReactNode }) => <>{children}</>
);
jest.mock('./pages/HomePage', () => () => <div data-testid="home-page">HomePage</div>);
jest.mock('./pages/SimulationPage', () => () => (
  <div data-testid="simulation-page">SimulationPage</div>
));
jest.mock('./pages/SimulationComparePage', () => () => (
  <div data-testid="simulation-compare-page">SimulationComparePage</div>
));
jest.mock('./pages/Login', () => () => <div data-testid="login-page">Login</div>);
jest.mock('./pages/Register', () => () => <div data-testid="register-page">Register</div>);
jest.mock('./pages/ProfilePage', () => () => <div data-testid="profile-page">ProfilePage</div>);
jest.mock('./pages/UserProfilePage', () => () => (
  <div data-testid="user-profile-page">UserProfilePage</div>
));
jest.mock('./pages/PartyPage', () => () => <div data-testid="party-page">PartyPage</div>);
jest.mock('./pages/PartyDetailPage', () => () => (
  <div data-testid="party-detail-page">PartyDetailPage</div>
));

// AuthGuard: render the component directly (bypass auth check)
jest.mock(
  './context/AuthGuard',
  () =>
    ({ component: Component }: { component: React.ComponentType }) => <Component />
);

jest.mock('./context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

describe('App', () => {
  const mockUseAuth = useAuth as jest.Mock;

  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: null });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('does not render Navbar on /login route', () => {
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
  });

  it('does not render Navbar on /register route', () => {
    window.history.pushState({}, '', '/register');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
  });

  it('renders Navbar on the home route', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('navbar')).toBeInTheDocument();
  });

  it('renders Login page when unauthenticated on /login', () => {
    mockUseAuth.mockReturnValue({ user: null });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('redirects to home when authenticated user visits /login', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders HomePage on / route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders ProfilePage on /profile route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/profile');
    render(<App />);
    expect(screen.getByTestId('profile-page')).toBeInTheDocument();
  });

  it('renders UserProfilePage on /users/:id route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/users/1');
    render(<App />);
    expect(screen.getByTestId('user-profile-page')).toBeInTheDocument();
  });

  it('renders SimulationPage on /simulation route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/simulation');
    render(<App />);
    expect(screen.getByTestId('simulation-page')).toBeInTheDocument();
  });

  it('renders SimulationComparePage on /simulation/compare route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/simulation/compare');
    render(<App />);
    expect(screen.getByTestId('simulation-compare-page')).toBeInTheDocument();
  });
});
