import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navbar from './Navbar';
import { useAuth } from '../stores/useAuthStore';
import { useTheme, useExpertMode, useTeacherMode } from '../stores/useUIStore';

vi.mock('../stores/useAuthStore', async () => ({
  ...(await vi.importActual('../stores/useAuthStore')),
  useAuth: vi.fn(),
}));
vi.mock('../stores/useUIStore', () => ({
  useTheme: vi.fn(),
  useExpertMode: vi.fn(),
  useTeacherMode: vi.fn(),
}));
vi.mock('../i18n', () => ({
  default: { language: 'en', changeLanguage: vi.fn() },
  switchLanguage: vi.fn(),
}));

function renderNavbar(user: { username: string; role: string } | null = null) {
  (useAuth as jest.Mock).mockReturnValue({ user, logout: vi.fn(), loading: false });
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
    (useTeacherMode as jest.Mock).mockReturnValue({
      teacherMode: false,
      setTeacherMode: vi.fn(),
      slides: [],
    });
  });

  it('renders the Vote Lab brand', () => {
    renderNavbar();
    expect(screen.getByText('Vote Lab')).toBeInTheDocument();
  });

  it('renders Election Lab link (may include emoji)', () => {
    renderNavbar();
    // The link may render as "🔬 Election Lab" — match by partial text
    expect(screen.getByText(/Election Lab/i)).toBeInTheDocument();
  });

  it('renders Learn and Explore dropdown toggles', () => {
    renderNavbar();
    expect(screen.getByText(/learn|apprendre/i)).toBeInTheDocument();
    expect(screen.getByText(/explore|explorer/i)).toBeInTheDocument();
  });

  it('shows settings toggle when not authenticated', () => {
    renderNavbar();
    // The user/settings dropdown toggle should be visible
    expect(
      screen.getByRole('button', { name: /user-settings-dropdown|settings|préférences/i }) ??
        screen.getByText(/settings|préférences/i)
    ).toBeTruthy();
  });

  it('shows username in toggle button when authenticated', () => {
    renderNavbar({ username: 'alice', role: 'User' });
    // Username appears in the dropdown toggle button
    expect(screen.getByText('alice')).toBeInTheDocument();
  });

  it('renders dropdown toggle differently for logged-in vs guest', () => {
    const { unmount } = renderNavbar({ username: 'bob', role: 'User' });
    expect(screen.getByText('bob')).toBeInTheDocument();
    unmount();

    renderNavbar();
    expect(screen.queryByText('bob')).not.toBeInTheDocument();
  });

  it('returns null while loading', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null, logout: vi.fn(), loading: true });
    const { container } = render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
    expect(container.innerHTML).toBe('');
  });
});
