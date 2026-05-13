import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, useTheme } from './ThemeContext';

const TestConsumer = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button data-testid="toggle-btn" onClick={toggleTheme}>
        Toggle
      </button>
    </div>
  );
};

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-bs-theme');
  });

  it('renders children', () => {
    render(
      <ThemeProvider>
        <div data-testid="child">child</div>
      </ThemeProvider>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('defaults to light theme', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
  });

  it('toggles from light to dark', async () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByTestId('toggle-btn'));
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });

  it('toggles from dark to light', () => {
    localStorage.setItem('votelab_theme', 'dark');
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    fireEvent.click(screen.getByTestId('toggle-btn'));
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
  });

  it('persists theme to localStorage on toggle', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByTestId('toggle-btn'));
    expect(localStorage.getItem('votelab_theme')).toBe('dark');
  });

  it('sets data-bs-theme attribute on html element', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('light');
  });

  it('updates data-bs-theme attribute on toggle', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByTestId('toggle-btn'));
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
  });
});
