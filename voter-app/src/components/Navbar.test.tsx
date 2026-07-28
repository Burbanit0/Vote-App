import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
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

  it('renders the three destinations: Playground → Laboratoire → À vous de jouer', () => {
    const { container } = renderNavbar();
    const hrefs = Array.from(container.querySelectorAll('nav a[href^="/"]')).map((a) =>
      a.getAttribute('href')
    );
    expect(hrefs).toEqual(
      expect.arrayContaining(['/playground', '/laboratoire', '/a-vous-de-jouer'])
    );
    expect(hrefs.indexOf('/playground')).toBeLessThan(hrefs.indexOf('/laboratoire'));
    expect(hrefs.indexOf('/laboratoire')).toBeLessThan(hrefs.indexOf('/a-vous-de-jouer'));
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
