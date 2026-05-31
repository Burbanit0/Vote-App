import { render, screen, fireEvent } from '@testing-library/react';
import { useUIStore, useTheme, useExpertMode } from './useUIStore';

const ThemeConsumer = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button data-testid="toggle" onClick={toggleTheme}>toggle</button>
    </div>
  );
};

const ExpertConsumer = () => {
  const { expertMode, setExpertMode } = useExpertMode();
  return (
    <div>
      <span data-testid="expert">{expertMode ? 'on' : 'off'}</span>
      <button data-testid="enable" onClick={() => setExpertMode(true)}>on</button>
      <button data-testid="disable" onClick={() => setExpertMode(false)}>off</button>
    </div>
  );
};

beforeEach(() => {
  localStorage.clear();
  useUIStore.setState({ theme: 'light', expertMode: false });
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

describe('useUIStore — expert mode', () => {
  it('defaults off, enables/disables, persists', () => {
    render(<ExpertConsumer />);
    expect(screen.getByTestId('expert')).toHaveTextContent('off');
    fireEvent.click(screen.getByTestId('enable'));
    expect(screen.getByTestId('expert')).toHaveTextContent('on');
    expect(localStorage.getItem('votelab_expert')).toBe('true');
    fireEvent.click(screen.getByTestId('disable'));
    expect(screen.getByTestId('expert')).toHaveTextContent('off');
    expect(localStorage.getItem('votelab_expert')).toBe('false');
  });

  it('hydrate() restores expert mode from localStorage', () => {
    localStorage.setItem('votelab_expert', 'true');
    useUIStore.getState().hydrate();
    render(<ExpertConsumer />);
    expect(screen.getByTestId('expert')).toHaveTextContent('on');
  });
});

describe('useUIStore — teacher slides', () => {
  it('adds and removes slides (persisted)', () => {
    useUIStore.setState({ slides: [] });
    useUIStore.getState().addSlide({ type: 'captured', title: 'A', content: {} });
    expect(useUIStore.getState().slides).toHaveLength(1);
    const id = useUIStore.getState().slides[0].id;
    useUIStore.getState().removeSlide(id);
    expect(useUIStore.getState().slides).toHaveLength(0);
  });
});
