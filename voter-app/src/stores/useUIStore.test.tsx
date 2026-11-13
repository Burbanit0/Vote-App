import { render, screen, fireEvent } from '@testing-library/react';
import { useUIStore, useTheme, usePlainLanguage } from './useUIStore';

const ThemeConsumer = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button data-testid="toggle" onClick={toggleTheme}>
        toggle
      </button>
    </div>
  );
};

const PlainConsumer = () => {
  const { plainLanguage, setPlainLanguage } = usePlainLanguage();
  return (
    <div>
      <span data-testid="plain">{plainLanguage ? 'on' : 'off'}</span>
      <button data-testid="enable" onClick={() => setPlainLanguage(true)}>
        on
      </button>
      <button data-testid="disable" onClick={() => setPlainLanguage(false)}>
        off
      </button>
    </div>
  );
};

beforeEach(() => {
  localStorage.clear();
  useUIStore.setState({ theme: 'light', plainLanguage: false });
});

describe('useUIStore — theme', () => {
  it('defaults to light and toggles to dark (persisted + applied to <html>)', () => {
    render(<ThemeConsumer />);
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    fireEvent.click(screen.getByTestId('toggle'));
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    expect(localStorage.getItem('votelab_theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
  });

  it('hydrate() restores theme from localStorage', () => {
    localStorage.setItem('votelab_theme', 'dark');
    useUIStore.getState().hydrate();
    render(<ThemeConsumer />);
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });
});

describe('useUIStore — plain language', () => {
  it('defaults off, enables/disables, persists', () => {
    render(<PlainConsumer />);
    expect(screen.getByTestId('plain')).toHaveTextContent('off');
    fireEvent.click(screen.getByTestId('enable'));
    expect(screen.getByTestId('plain')).toHaveTextContent('on');
    expect(localStorage.getItem('votelab_plain')).toBe('true');
    fireEvent.click(screen.getByTestId('disable'));
    expect(screen.getByTestId('plain')).toHaveTextContent('off');
    expect(localStorage.getItem('votelab_plain')).toBe('false');
  });

  it('hydrate() restores plain language from localStorage', () => {
    localStorage.setItem('votelab_plain', 'true');
    useUIStore.getState().hydrate();
    render(<PlainConsumer />);
    expect(screen.getByTestId('plain')).toHaveTextContent('on');
  });
});

describe('useUIStore — the retired Beginner/Expert level', () => {
  it('has no level in its state, and ignores the key an earlier version left in storage', () => {
    localStorage.setItem('votelab_expert', 'true');
    useUIStore.getState().hydrate();
    const state = useUIStore.getState() as unknown as Record<string, unknown>;
    expect(state).not.toHaveProperty('expertMode');
    expect(state).not.toHaveProperty('setExpertMode');
  });
});
