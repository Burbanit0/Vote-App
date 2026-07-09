import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navbar from './Navbar';
import { useTheme, useExpertMode } from '../stores/useUIStore';

vi.mock('../stores/useUIStore', () => ({
  useTheme: vi.fn(),
  useExpertMode: vi.fn(),
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
  });

  it('renders the Vote Lab brand', () => {
    renderNavbar();
    expect(screen.getByText('Vote Lab')).toBeInTheDocument();
  });

  it('renders the two destinations: Playground + Laboratoire', () => {
    const { container } = renderNavbar();
    expect(container.querySelector('a[href="/playground"]')).toBeInTheDocument();
    expect(container.querySelector('a[href="/laboratoire"]')).toBeInTheDocument();
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
