import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import Navbar from './Navbar';
import { useTheme, useExpertMode, usePlainLanguage } from '../stores/useUIStore';

vi.mock('../stores/useUIStore', () => ({
  useTheme: vi.fn(),
  useExpertMode: vi.fn(),
  usePlainLanguage: vi.fn(),
}));
vi.mock('../i18n', () => ({
  default: { language: 'en', changeLanguage: vi.fn() },
  switchLanguage: vi.fn(),
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
    vi.clearAllMocks();
    (useTheme as jest.Mock).mockReturnValue({ theme: 'light', toggleTheme: vi.fn() });
    (useExpertMode as jest.Mock).mockReturnValue({ expertMode: false, setExpertMode: vi.fn() });
    (usePlainLanguage as jest.Mock).mockReturnValue({
      plainLanguage: false,
      setPlainLanguage: vi.fn(),
    });
  });

  it('renders the Vote Lab brand', () => {
    renderNavbar();
    expect(screen.getByText('Vote Lab')).toBeInTheDocument();
  });

  it('renders the four destinations: Playground → Laboratoire → À vous de jouer → Polity', () => {
    const { container } = renderNavbar();
    const hrefs = Array.from(container.querySelectorAll('nav a[href^="/"]')).map((a) =>
      a.getAttribute('href')
    );
    expect(hrefs).toEqual(
      expect.arrayContaining(['/playground', '/laboratoire', '/a-vous-de-jouer', '/polity'])
    );
    expect(hrefs.indexOf('/playground')).toBeLessThan(hrefs.indexOf('/laboratoire'));
    expect(hrefs.indexOf('/laboratoire')).toBeLessThan(hrefs.indexOf('/a-vous-de-jouer'));
    expect(hrefs.indexOf('/a-vous-de-jouer')).toBeLessThan(hrefs.indexOf('/polity'));
    expect(screen.getByTestId('nav-polity')).toHaveTextContent('Polity');
  });

  it('tells assistive tech which destination is the current page', () => {
    const original = window.location.pathname;
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/a-vous-de-jouer' },
      writable: true,
    });
    const { container } = renderNavbar();
    expect(container.querySelector('a[href="/a-vous-de-jouer"]')).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(container.querySelector('a[href="/playground"]')).not.toHaveAttribute('aria-current');
    expect(screen.getByTestId('nav-polity')).not.toHaveAttribute('aria-current');
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: original },
      writable: true,
    });
  });

  it('marks Polity as the current page there, and a click on it closes the collapsed menu', () => {
    const original = window.location.pathname;
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/polity' },
      writable: true,
    });
    renderNavbar();
    const link = screen.getByTestId('nav-polity');
    expect(link).toHaveAttribute('aria-current', 'page');
    fireEvent.click(screen.getByTestId('navbar-toggle'));
    expect(screen.getByTestId('navbar-toggle')).toHaveAttribute('aria-expanded', 'true');
    link.addEventListener('click', (e) => e.preventDefault());
    fireEvent.click(link);
    expect(screen.getByTestId('navbar-toggle')).toHaveAttribute('aria-expanded', 'false');
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: original },
      writable: true,
    });
  });

  it('has no Learn/Explore dropdowns and no auth links', () => {
    const { container } = renderNavbar();
    expect(screen.queryByText(/^learn$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^explore$/i)).not.toBeInTheDocument();
    expect(container.querySelector('a[href="/login"]')).not.toBeInTheDocument();
    expect(container.querySelector('a[href="/profile"]')).not.toBeInTheDocument();
  });

  it('shows the settings dropdown toggle', () => {
    renderNavbar();
    expect(screen.getByText(/settings/i)).toBeInTheDocument();
  });
});
