import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

const Child: React.FC = () => <div>child content</div>;
const Broken: React.FC = () => { throw new Error('test error'); };

beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(<ErrorBoundary><Child /></ErrorBoundary>);
    expect(screen.getByText('child content')).toBeInTheDocument();
  });

  it('renders fallback on error', () => {
    render(<ErrorBoundary><Broken /></ErrorBoundary>);
    expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
  });
});
