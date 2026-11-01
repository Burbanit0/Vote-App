import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HomeEntrance from '../HomeEntrance';
import { fakeMedia, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
beforeEach(() => {
  fakeMedia({});
  sessionStorage.clear();
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  vi.useRealTimers();
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

const entrance = () => screen.queryByTestId('home-entrance');

describe('HomeEntrance', () => {
  it('counts to 100, folds into the brand mark, then hands over — once a session', () => {
    vi.useFakeTimers();
    const frames = manualFrames();
    const mark = document.createElement('span');
    mark.setAttribute('data-brand-mark', '');
    vi.spyOn(mark, 'getBoundingClientRect').mockReturnValue({ left: 40, top: 10 } as DOMRect);
    document.body.appendChild(mark);
    const onDone = vi.fn();
    const { unmount } = render(<HomeEntrance onReveal={onDone} />);
    expect(entrance()).toHaveAttribute('data-phase', 'count');
    frames.flush();
    const columns = entrance()!.querySelectorAll('.flex-col');
    expect((columns[0] as HTMLElement).style.transform).toBe('translateY(-1em)');
    expect(onDone).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(1150));
    expect(entrance()).toHaveAttribute('data-phase', 'wipe');
    expect(entrance()!.style.clipPath).toContain('41.0px 11.0px');
    // The page settles in while the screen folds away.
    expect(onDone).toHaveBeenCalledTimes(1);
    act(() => void vi.advanceTimersByTime(1000));
    expect(entrance()).toBeNull();
    expect(onDone).toHaveBeenCalledTimes(1);
    unmount();
    render(<HomeEntrance onReveal={onDone} />);
    expect(entrance()).toBeNull();
  });

  it('folds into the corner when there is no brand mark', () => {
    vi.useFakeTimers();
    render(<HomeEntrance onReveal={vi.fn()} />);
    act(() => void vi.advanceTimersByTime(1150));
    expect(entrance()!.style.clipPath).toContain('17.0px 13.0px');
  });

  it('ends at once on a key, a click or the wheel, and stops counting', () => {
    const frames = manualFrames();
    const onDone = vi.fn();
    render(<HomeEntrance onReveal={onDone} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(entrance()).toBeNull();
    expect(onDone).toHaveBeenCalled();
    expect(() => frames.flush()).not.toThrow();
    expect(frames.pending()).toBe(0);
  });

  it('never plays under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    const onDone = vi.fn();
    render(<HomeEntrance onReveal={onDone} />);
    expect(entrance()).toBeNull();
    expect(onDone).toHaveBeenCalled();
  });

  it('never plays when the session storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    render(<HomeEntrance onReveal={vi.fn()} />);
    expect(entrance()).toBeNull();
  });

  it('still plays when only writing to the session storage fails', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('full');
    });
    render(<HomeEntrance onReveal={vi.fn()} />);
    expect(entrance()).toHaveAttribute('data-phase', 'count');
  });
});
