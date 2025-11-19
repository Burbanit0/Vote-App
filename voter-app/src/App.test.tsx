import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import { useAuth } from './context/AuthContext';

// Mock child components
jest.mock('./components/Navbar', () => () => <div data-testid="navbar">Navbar</div>);
jest.mock('./components/Election/ElectionForm', () => () => <div data-testid="election-form">ElectionForm</div>);
jest.mock('./components/Route/ErrorBoundary', () => ({ children }: { children: React.ReactNode }) => <>{children}</>);
jest.mock('./pages/HomePage', () => () => <div data-testid="home-page">HomePage</div>);
jest.mock('./pages/SimulationPage', () => () => <div data-testid="simulation-page">SimulationPage</div>);
jest.mock('./pages/ElectionDetailPage', () => () => <div data-testid="election-detail-page">ElectionDetailPage</div>);
jest.mock('./pages/Login', () => () => <div data-testid="login-page">Login</div>);
jest.mock('./pages/Register', () => () => <div data-testid="register-page">Register</div>);
jest.mock('./pages/ProfilePage', () => () => <div data-testid="profile-page">ProfilePage</div>);
jest.mock('./pages/UserProfilePage', () => () => <div data-testid="user-profile-page">UserProfilePage</div>);
jest.mock('./pages/PartyPage', () => () => <div data-testid="party-page">PartyPage</div>);
jest.mock('./pages/PartyDetailPage', () => () => <div data-testid="party-detail-page">PartyDetailPage</div>);

// Mock AuthGuard
jest.mock('./context/AuthGuard', () => ({ component: Component }: { component: React.ComponentType }) => (
  <Component />
));

// Mock useAuth
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

  it('does not render Navbar on /login and /register routes', () => {
    // Use `window.history.pushState` to simulate navigation
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();

    window.history.pushState({}, '', '/register');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
  });

  it('renders Navbar on other routes', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('navbar')).toBeInTheDocument();
  });

  it('renders Login page when not authenticated and on /login route', () => {
    mockUseAuth.mockReturnValue({ user: null });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('redirects to home page when authenticated and accessing /login', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders HomePage when authenticated and on / route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders ElectionForm for /create_election route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/create_election');
    render(<App />);
    expect(screen.getByTestId('election-form')).toBeInTheDocument();
  });

  it('renders ElectionDetail for /elections/:id route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/elections/1');
    render(<App />);
    expect(screen.getByTestId('election-detail-page')).toBeInTheDocument();
  });

  it('renders ProfilePage for /profile route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/profile');
    render(<App />);
    expect(screen.getByTestId('profile-page')).toBeInTheDocument();
  });

  it('renders UserProfilePage for /users/:id route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/users/1');
    render(<App />);
    expect(screen.getByTestId('user-profile-page')).toBeInTheDocument();
  });

  it('renders PartyPage for /parties route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/parties');
    render(<App />);
    expect(screen.getByTestId('party-page')).toBeInTheDocument();
  });

  it('renders PartyDetailPage for /parties/:party_id route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/parties/1');
    render(<App />);
    expect(screen.getByTestId('party-detail-page')).toBeInTheDocument();
  });

  it('renders SimulationPage for /simulation route', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/simulation');
    render(<App />);
    expect(screen.getByTestId('simulation-page')).toBeInTheDocument();
  });
});
