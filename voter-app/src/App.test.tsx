import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Link, useNavigate } from 'react-router';
import App, { ScrollToTop } from './App';

vi.mock('./components/Navbar', () => ({ default: () => <div data-testid="navbar">Navbar</div> }));
vi.mock('./components/Route/ErrorBoundary', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('./pages/HomePage', () => ({ default: () => <div data-testid="home-page">HomePage</div> }));
vi.mock('./pages/PlaygroundPage', () => ({
  default: () => <div data-testid="playground-page">PlaygroundPage</div>,
}));
vi.mock('./pages/LaboratoirePage', () => ({
  default: () => <div data-testid="laboratoire-page">LaboratoirePage</div>,
}));
vi.mock('./pages/NotFoundPage', () => ({
  default: () => <div data-testid="not-found-page">NotFoundPage</div>,
}));

// ── Tests ──────────────────────────────────────────────────────────────────

describe('App routing (anonymous, two destinations)', () => {
  afterEach(() => vi.clearAllMocks());

  it('shows the Navbar', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('navbar')).toBeInTheDocument();
  });

  it('renders HomePage on /', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders PlaygroundPage on /playground', async () => {
    window.history.pushState({}, '', '/playground');
    render(<App />);
    expect(await screen.findByTestId('playground-page')).toBeInTheDocument();
  });

  it('renders LaboratoirePage on /laboratoire', async () => {
    window.history.pushState({}, '', '/laboratoire');
    render(<App />);
    expect(await screen.findByTestId('laboratoire-page')).toBeInTheDocument();
  });

  it('redirects retired content routes to the laboratoire (e.g. /theory, /galerie)', async () => {
    window.history.pushState({}, '', '/theory');
    render(<App />);
    expect(await screen.findByTestId('laboratoire-page')).toBeInTheDocument();
  });

  it('redirects legacy/simulator routes to the playground (e.g. /simulation/compare)', async () => {
    window.history.pushState({}, '', '/simulation/compare');
    render(<App />);
    expect(await screen.findByTestId('playground-page')).toBeInTheDocument();
  });

  it('redirects old auth routes to home (e.g. /login, /profile)', () => {
    window.history.pushState({}, '', '/login');
    render(<App />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders NotFoundPage on an unknown route', async () => {
    window.history.pushState({}, '', '/this-route-does-not-exist');
    render(<App />);
    expect(await screen.findByTestId('not-found-page')).toBeInTheDocument();
  });
});

describe('ScrollToTop', () => {
  const Back: React.FC = () => {
    const navigate = useNavigate();
    return <button onClick={() => navigate(-1)}>back</button>;
  };

  it('scrolls to the top on a link to another page, not on back', () => {
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    render(
      <MemoryRouter initialEntries={['/decouvrir']}>
        <ScrollToTop />
        <Link to="/playground">go</Link>
        <Back />
      </MemoryRouter>
    );
    expect(scrollTo).not.toHaveBeenCalled(); // first load is a POP: the browser's position stands
    fireEvent.click(screen.getByText('go'));
    expect(scrollTo).toHaveBeenCalledWith(0, 0);
    scrollTo.mockClear();
    fireEvent.click(screen.getByText('back'));
    expect(scrollTo).not.toHaveBeenCalled();
    scrollTo.mockRestore();
  });
});
