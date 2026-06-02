import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import { useAuth } from './stores/useAuthStore';

// ── Component mocks ────────────────────────────────────────────────────────

vi.mock('./components/Navbar', () => ({ default: () => <div data-testid="navbar">Navbar</div> }));
vi.mock(
  './components/Route/ErrorBoundary',
  () => ({ default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

vi.mock('./pages/HomePage', () => ({ default: () => <div data-testid="home-page">HomePage</div> }));
vi.mock('./pages/SimulationPage', () => ({ default: () => (
  <div data-testid="simulation-page">SimulationPage</div>
) }));
vi.mock('./pages/SimulationComparePage', () => ({ default: () => (
  <div data-testid="simulation-compare-page">SimulationComparePage</div>
) }));
vi.mock('./pages/ScenarioBuilderPage', () => ({ default: () => (
  <div data-testid="scenario-builder-page">ScenarioBuilderPage</div>
) }));
vi.mock('./pages/ConstitutionalCrisisPage', () => ({ default: () => (
  <div data-testid="constitutional-crisis-page">ConstitutionalCrisisPage</div>
) }));
vi.mock('./pages/Login', () => ({ default: () => <div data-testid="login-page">Login</div> }));
vi.mock('./pages/Register', () => ({ default: () => <div data-testid="register-page">Register</div> }));
vi.mock('./pages/ProfilePage', () => ({ default: () => (
  <div data-testid="profile-page">ProfilePage</div>
) }));
vi.mock('./pages/UserProfilePage', () => ({ default: () => (
  <div data-testid="user-profile-page">UserProfilePage</div>
) }));

// AuthGuard: render the wrapped component directly (skip auth logic in tests)
vi.mock(
  './components/Route/AuthGuard',
  () => ({ default: ({ component: Component }: { component: React.ComponentType }) => <Component /> }));

vi.mock('./stores/useAuthStore', async () => ({
  ...(await vi.importActual('./stores/useAuthStore')),
  useAuth: vi.fn(),
}));

// ── Tests ──────────────────────────────────────────────────────────────────

describe('App', () => {
  const mockUseAuth = useAuth as jest.Mock;

  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: null });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Navbar visibility
  it('hides Navbar on /login', () => {
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
  });

  it('hides Navbar on /register', () => {
    window.history.pushState({}, '', '/register');
    render(<App />);
    expect(screen.queryByTestId('navbar')).not.toBeInTheDocument();
  });

  it('shows Navbar on all other routes', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('navbar')).toBeInTheDocument();
  });

  // Auth routes
  it('renders Login when unauthenticated on /login', () => {
    mockUseAuth.mockReturnValue({ user: null });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('redirects to / when authenticated user visits /login', () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  // Public routes (no account required)
  it('renders HomePage on / — public route', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  // NOTE: every route below was made lazy in A1 (commit a6497ad) so we need
  // findByTestId (async) — getByTestId returns before Suspense resolves.

  it('renders ScenarioBuilderPage on /scenario-builder', async () => {
    window.history.pushState({}, '', '/scenario-builder');
    render(<App />);
    expect(await screen.findByTestId('scenario-builder-page')).toBeInTheDocument();
  });

  it('renders SimulationComparePage on /simulation/compare', async () => {
    window.history.pushState({}, '', '/simulation/compare');
    render(<App />);
    expect(await screen.findByTestId('simulation-compare-page')).toBeInTheDocument();
  });

  it('renders ConstitutionalCrisisPage on /constitutional-crisis', async () => {
    window.history.pushState({}, '', '/constitutional-crisis');
    render(<App />);
    expect(await screen.findByTestId('constitutional-crisis-page')).toBeInTheDocument();
  });

  // Auth-protected routes
  it('renders ProfilePage on /profile', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/profile');
    render(<App />);
    expect(await screen.findByTestId('profile-page')).toBeInTheDocument();
  });

  it('renders UserProfilePage on /users/:id', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/users/1');
    render(<App />);
    expect(await screen.findByTestId('user-profile-page')).toBeInTheDocument();
  });

  it('renders SimulationPage on /simulation', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'Test User' } });
    window.history.pushState({}, '', '/simulation');
    render(<App />);
    expect(await screen.findByTestId('simulation-page')).toBeInTheDocument();
  });
});
