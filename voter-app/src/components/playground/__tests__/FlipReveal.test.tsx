import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';

import FlipReveal from '../FlipReveal';

describe('FlipReveal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders children and no caption on first mount', () => {
    render(
      <FlipReveal modeKey="leader" caption="Mêmes électeurs, caractère opposé.">
        <div data-testid="inner">canvas</div>
      </FlipReveal>
    );
    expect(screen.getByTestId('inner')).toBeInTheDocument();
    expect(screen.queryByTestId('flip-caption')).not.toBeInTheDocument();
  });

  it('shows the caption on mode change (both directions) and hides it after the delay', () => {
    const { rerender } = render(
      <FlipReveal modeKey="leader" caption="Mêmes électeurs, caractère opposé.">
        <div>a</div>
      </FlipReveal>
    );

    // leader → parliament
    rerender(
      <FlipReveal modeKey="parliament" caption="Mêmes électeurs, caractère opposé.">
        <div>b</div>
      </FlipReveal>
    );
    expect(screen.getByTestId('flip-caption')).toHaveTextContent('Mêmes électeurs');

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.queryByTestId('flip-caption')).not.toBeInTheDocument();

    // parliament → leader (replayable, reverse direction)
    rerender(
      <FlipReveal modeKey="leader" caption="Mêmes électeurs, caractère opposé.">
        <div>a</div>
      </FlipReveal>
    );
    expect(screen.getByTestId('flip-caption')).toBeInTheDocument();
  });

  it('restarts the enter animation on each flip', () => {
    const { rerender } = render(
      <FlipReveal modeKey="leader" caption="c">
        <div>a</div>
      </FlipReveal>
    );
    rerender(
      <FlipReveal modeKey="parliament" caption="c">
        <div>b</div>
      </FlipReveal>
    );
    // Immediately after the flip the stage is in its hidden (pre-enter) state.
    expect(screen.getByTestId('flip-stage').style.opacity).toBe('0');
  });
});
