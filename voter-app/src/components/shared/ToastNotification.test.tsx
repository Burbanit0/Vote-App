import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { ToastProvider, useToast } from './ToastNotification';

const TestConsumer: React.FC = () => {
  const { success, error, info } = useToast();
  return (
    <div>
      <button data-testid="btn-success" onClick={() => success('Saved!')}>
        Success
      </button>
      <button data-testid="btn-error" onClick={() => error('Failed!')}>
        Error
      </button>
      <button data-testid="btn-info" onClick={() => info('FYI')}>
        Info
      </button>
    </div>
  );
};

function renderPage() {
  return render(
    <ToastProvider>
      <TestConsumer />
    </ToastProvider>
  );
}

describe('ToastNotification', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('shows a success toast with the message', () => {
    renderPage();
    act(() => {
      fireEvent.click(screen.getByTestId('btn-success'));
    });
    expect(screen.getByText('Saved!')).toBeInTheDocument();
  });

  it('shows an error toast with the message', () => {
    renderPage();
    act(() => {
      fireEvent.click(screen.getByTestId('btn-error'));
    });
    expect(screen.getByText('Failed!')).toBeInTheDocument();
  });

  it('shows an info toast with the message', () => {
    renderPage();
    act(() => {
      fireEvent.click(screen.getByTestId('btn-info'));
    });
    expect(screen.getByText('FYI')).toBeInTheDocument();
  });
});
