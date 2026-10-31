import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import MomentsTrack from '../MomentsTrack';
import { fakeMedia, fakeScroll, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
const realScrollTo = window.scrollTo;
afterEach(() => {
  window.matchMedia = realMatchMedia;
  window.scrollTo = realScrollTo;
  vi.restoreAllMocks();
});

const renderTrack = () =>
  render(
    <MemoryRouter>
      <MomentsTrack />
    </MemoryRouter>
  );
const numerals = () => screen.getAllByText(/^[1-5]$/);

describe('MomentsTrack', () => {
  it('is a plain list on a phone: no pin, everything drawn', () => {
    fakeMedia({});
    renderTrack();
    expect(screen.getByTestId('home-moments')).not.toHaveClass('h-[400vh]');
    numerals().forEach((n) => expect(n).toHaveStyle({ transform: 'none' }));
    expect(screen.getAllByRole('link')).toHaveLength(5);
    const scrollTo = vi.spyOn(window, 'scrollTo');
    fireEvent.focus(screen.getAllByRole('link')[2]);
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('stays a list under reduced motion, even on a desktop', () => {
    fakeMedia({ 'min-width': true, 'prefers-reduced-motion': true });
    renderTrack();
    expect(screen.getByTestId('home-moments')).not.toHaveClass('h-[400vh]');
  });

  it('pins on a desktop and draws the moments in as the page scrolls', () => {
    fakeMedia({ 'min-width': true });
    const frames = manualFrames();
    const scroll = fakeScroll(0);
    const { container, unmount } = renderTrack();
    const section = screen.getByTestId('home-moments');
    expect(section).toHaveClass('h-[400vh]');
    Object.defineProperty(section, 'offsetHeight', {
      configurable: true,
      value: 4 * window.innerHeight,
    });
    act(() => void frames.flush());
    expect(numerals()[0]).toHaveStyle({ transform: 'none' });
    expect(numerals()[4]).toHaveStyle({ transform: 'translateY(100%)' });
    scroll.set(3 * window.innerHeight);
    act(() => void frames.flush());
    numerals().forEach((n) => expect(n).toHaveStyle({ transform: 'none' }));
    const glyph = container.querySelector('article path') as SVGPathElement;
    expect(Number(glyph.style.strokeDashoffset)).toBe(0);
    // Tabbing to a panel scrolls the page to where the track shows it.
    fireEvent.focus(screen.getAllByRole('link')[2]);
    expect(scroll.scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: 'auto' });
    const off = vi.spyOn(window, 'removeEventListener');
    unmount();
    expect(off).toHaveBeenCalledWith('scroll', expect.any(Function));
  });
});
