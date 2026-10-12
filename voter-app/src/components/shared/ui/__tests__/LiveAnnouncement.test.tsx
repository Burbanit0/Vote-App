import React from 'react';
import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LiveAnnouncement from '../LiveAnnouncement';

describe('LiveAnnouncement', () => {
  afterEach(() => vi.useRealTimers());

  it('speaks only where the text settles, not every step on the way', () => {
    vi.useFakeTimers();
    const { rerender } = render(<LiveAnnouncement testId="say" text="Alice wins" />);
    const region = screen.getByTestId('say');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveTextContent('');
    act(() => vi.advanceTimersByTime(500));
    rerender(<LiveAnnouncement testId="say" text="Bob wins" />);
    act(() => vi.advanceTimersByTime(500));
    expect(region).toHaveTextContent(''); // Alice never held long enough to be spoken
    act(() => vi.advanceTimersByTime(400));
    expect(region).toHaveTextContent('Bob wins');
  });
});
