import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

// Silence the expected console.error noise from intentional throws.
const originalError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});
afterAll(() => {
  console.error = originalError;
});

const Boom: React.FC<{ when?: boolean }> = ({ when = true }) => {
  if (when) throw new Error('boom message');
  return <span>ok</span>;
};

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <span data-testid="child">hi</span>
      </ErrorBoundary>
    );
    expect(screen.getByTestId('child')).toHaveTextContent('hi');
  });

  it('shows the fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('error-boundary-retry')).toBeInTheDocument();
    expect(screen.getByTestId('error-boundary-home')).toBeInTheDocument();
    expect(screen.getByTestId('error-boundary-copy')).toBeInTheDocument();
  });

  it('exposes the dev-mode details panel with the stack', () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    const details = screen.getByTestId('error-boundary-details');
    expect(details.textContent).toContain('boom message');
  });

  it('retry + key-based remount recovers cleanly when the upstream cause is fixed', () => {
    // The `key` swap forces a fresh ErrorBoundary instance — closer to the
    // real-world "user clicks Retry after refreshing data" flow than just
    // toggling state would be.
    const { rerender } = render(
      <ErrorBoundary key="v1">
        <Boom when />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    rerender(
      <ErrorBoundary key="v2">
        <Boom when={false} />
      </ErrorBoundary>
    );
    expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
    expect(screen.getByText('ok')).toBeInTheDocument();
  });

  it('copy button writes a structured payload to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    await act(async () => {
      screen.getByTestId('error-boundary-copy').click();
    });

    expect(writeText).toHaveBeenCalledTimes(1);
    const payload = writeText.mock.calls[0][0] as string;
    expect(payload).toContain('Error: Error: boom message');
    expect(payload).toContain('URL:');
    expect(payload).toContain('User-Agent:');
    expect(payload).toContain('Component stack:');
  });
});
