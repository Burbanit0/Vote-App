import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExpertModeProvider, useExpertMode } from './ExpertModeContext';

const TestConsumer = () => {
  const { expertMode, setExpertMode } = useExpertMode();
  return (
    <div>
      <span data-testid="expert">{expertMode ? 'on' : 'off'}</span>
      <button data-testid="enable-btn" onClick={() => setExpertMode(true)}>
        Enable
      </button>
      <button data-testid="disable-btn" onClick={() => setExpertMode(false)}>
        Disable
      </button>
    </div>
  );
};

describe('ExpertModeContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders children', () => {
    render(
      <ExpertModeProvider>
        <div data-testid="child">child</div>
      </ExpertModeProvider>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('defaults to false', () => {
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    expect(screen.getByTestId('expert')).toHaveTextContent('off');
  });

  it('enables expert mode', async () => {
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    fireEvent.click(screen.getByTestId('enable-btn'));
    expect(screen.getByTestId('expert')).toHaveTextContent('on');
  });

  it('disables expert mode', async () => {
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    fireEvent.click(screen.getByTestId('enable-btn'));
    expect(screen.getByTestId('expert')).toHaveTextContent('on');
    fireEvent.click(screen.getByTestId('disable-btn'));
    expect(screen.getByTestId('expert')).toHaveTextContent('off');
  });

  it('persists to localStorage when enabled', async () => {
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    fireEvent.click(screen.getByTestId('enable-btn'));
    expect(localStorage.getItem('votelab_expert')).toBe('true');
  });

  it('persists to localStorage when disabled', async () => {
    localStorage.setItem('votelab_expert', 'true');
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    fireEvent.click(screen.getByTestId('disable-btn'));
    expect(localStorage.getItem('votelab_expert')).toBe('false');
  });

  it('restores from localStorage on mount', () => {
    localStorage.setItem('votelab_expert', 'true');
    render(
      <ExpertModeProvider>
        <TestConsumer />
      </ExpertModeProvider>
    );
    expect(screen.getByTestId('expert')).toHaveTextContent('on');
  });
});
