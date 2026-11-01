import React from 'react';
import { render } from '@testing-library/react';
import { useReveal } from './useReveal';

const realIO = window.IntersectionObserver;
let seen: (entries: { isIntersecting: boolean }[]) => void;
const disconnect = vi.fn();

beforeEach(() => {
  window.IntersectionObserver = class {
    constructor(cb: typeof seen) {
      seen = cb;
    }
    observe() {}
    disconnect = disconnect;
  } as unknown as typeof IntersectionObserver;
});
afterEach(() => {
  window.IntersectionObserver = realIO;
  disconnect.mockClear();
});

const Section: React.FC = () => <section data-reveal data-testid="s" ref={useReveal()} />;

describe('useReveal', () => {
  it('marks the section shown the first time it comes into view, then stops watching', () => {
    const { getByTestId } = render(<Section />);
    seen([{ isIntersecting: false }]);
    expect(getByTestId('s')).not.toHaveAttribute('data-shown');
    seen([{ isIntersecting: true }]);
    expect(getByTestId('s')).toHaveAttribute('data-shown');
    expect(disconnect).toHaveBeenCalled();
  });
});
