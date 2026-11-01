import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import Navbar from './Navbar';
import { switchLanguage } from '../i18n';
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

  it('closes the phone menu when the brand is followed', () => {
    renderNavbar();
    const toggle = screen.getByTestId('navbar-toggle');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByText('Vote Lab'));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('renders the Vote Lab brand', () => {
    renderNavbar();
    expect(screen.getByText('Vote Lab')).toBeInTheDocument();
  });

  it('renders the three destinations: Playground → Laboratoire → À vous de jouer, and not Polity', () => {
    const { container } = renderNavbar();
    const hrefs = Array.from(container.querySelectorAll('nav a[href^="/"]')).map((a) =>
      a.getAttribute('href')
    );
    expect(hrefs).toEqual(
      expect.arrayContaining(['/playground', '/laboratoire', '/a-vous-de-jouer'])
    );
    expect(hrefs.indexOf('/playground')).toBeLessThan(hrefs.indexOf('/laboratoire'));
    expect(hrefs.indexOf('/laboratoire')).toBeLessThan(hrefs.indexOf('/a-vous-de-jouer'));
    // Polity is a research run explorer, not the teaching path: linked from the home footer.
    expect(hrefs).not.toContain('/polity');
    expect(screen.queryByTestId('nav-polity')).toBeNull();
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
    expect(container.querySelector('a[href="/laboratoire"]')).not.toHaveAttribute('aria-current');
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: original },
      writable: true,
    });
  });

  it('marks the Laboratoire as the current page there, and a click on it closes the collapsed menu', () => {
    const original = window.location.pathname;
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/laboratoire' },
      writable: true,
    });
    const { container } = renderNavbar();
    const link = container.querySelector('a[href="/laboratoire"]') as HTMLElement;
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

  describe('the settings menu', () => {
    const open = () => fireEvent.click(screen.getByRole('button', { name: /settings/i }));

    it('switches the theme with a two-way choice, and ignores a click on the current one', () => {
      const toggleTheme = vi.fn();
      (useTheme as jest.Mock).mockReturnValue({ theme: 'light', toggleTheme });
      renderNavbar();
      open();
      expect(screen.getByTestId('theme-light')).toHaveAttribute('aria-checked', 'true');
      fireEvent.click(screen.getByTestId('theme-light'));
      expect(toggleTheme).not.toHaveBeenCalled();
      fireEvent.click(screen.getByTestId('theme-dark'));
      expect(toggleTheme).toHaveBeenCalledTimes(1);
    });

    it('shows the dark theme as chosen when it is', () => {
      (useTheme as jest.Mock).mockReturnValue({ theme: 'dark', toggleTheme: vi.fn() });
      renderNavbar();
      open();
      expect(screen.getByTestId('theme-dark')).toHaveAttribute('aria-checked', 'true');
    });

    it('switches the language, each named in itself', () => {
      renderNavbar();
      open();
      expect(screen.getByTestId('lang-en')).toHaveAttribute('aria-checked', 'true');
      fireEvent.click(screen.getByTestId('lang-fr'));
      expect(switchLanguage).toHaveBeenCalledWith('fr');
    });

    it('switches between the beginner and the expert level', () => {
      const setExpertMode = vi.fn();
      (useExpertMode as jest.Mock).mockReturnValue({ expertMode: false, setExpertMode });
      const { unmount } = renderNavbar();
      open();
      fireEvent.click(screen.getByTestId('level-expert'));
      expect(setExpertMode).toHaveBeenCalledWith(true);
      unmount();
      (useExpertMode as jest.Mock).mockReturnValue({ expertMode: true, setExpertMode });
      renderNavbar();
      open();
      fireEvent.click(screen.getByTestId('level-beginner'));
      expect(setExpertMode).toHaveBeenLastCalledWith(false);
    });

    it('turns plain language on and off with a switch', () => {
      const setPlainLanguage = vi.fn();
      (usePlainLanguage as jest.Mock).mockReturnValue({ plainLanguage: false, setPlainLanguage });
      const { unmount } = renderNavbar();
      open();
      const sw = screen.getByRole('switch', { name: /plain language/i });
      expect(sw).toHaveAttribute('aria-checked', 'false');
      fireEvent.click(sw);
      expect(setPlainLanguage).toHaveBeenCalledWith(true);
      unmount();
      (usePlainLanguage as jest.Mock).mockReturnValue({ plainLanguage: true, setPlainLanguage });
      renderNavbar();
      open();
      expect(screen.getByRole('switch', { name: /plain language/i })).toHaveAttribute(
        'aria-checked',
        'true'
      );
    });
  });
});
