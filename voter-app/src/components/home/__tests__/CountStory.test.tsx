import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CountStory from '../CountStory';
import { fakeMedia, fakeScroll, manualFrames } from '../../../test/frames';

// jsdom lays nothing out: the count's track sits at the top of the page, and a screen
// is window.innerHeight tall unless a test gives the pinned stage a height.
const H = window.innerHeight;
const realMatchMedia = window.matchMedia;
const realScrollTo = window.scrollTo;

let frames: ReturnType<typeof manualFrames>;
let scroll: ReturnType<typeof fakeScroll>;
beforeEach(() => {
  fakeMedia({});
  frames = manualFrames();
  scroll = fakeScroll(0);
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  window.scrollTo = realScrollTo;
  vi.restoreAllMocks();
});

const settle = () => act(() => void frames.flush());
const svg = () => screen.getByRole('img');
const scrollTo = (screens: number) => {
  scroll.set(screens * H);
  settle();
};

describe('CountStory', () => {
  it('opens on the electorate, before the vote', () => {
    render(<CountStory />);
    settle();
    expect(svg()).toHaveAttribute('aria-label', '100 voters on a map, before the vote');
    expect(screen.getByTestId('home-count-tick-0')).toHaveAttribute('aria-current', 'step');
    // A scroll event that moves nothing redraws nothing.
    const ballot = svg().querySelector('rect[rx="1"]')!;
    const setAttribute = vi.spyOn(ballot, 'setAttribute');
    scroll.set(0);
    settle();
    expect(setAttribute).not.toHaveBeenCalled();
  });

  it('glides to each chapter and stamps its winner', () => {
    render(<CountStory />);
    settle();
    scrollTo(2.05);
    expect(svg()).toHaveAttribute('aria-label', 'Plurality: Bob elected with 45');
    expect(screen.getByText('Elected')).toBeInTheDocument();
    scrollTo(2.75);
    expect(screen.queryByText('Elected')).toBeNull();
    scrollTo(3.05);
    expect(svg()).toHaveAttribute('aria-label', 'Runoff: Alice elected 54 to 46');
    scrollTo(5);
    expect(svg()).toHaveAttribute('aria-label', 'Three rules, three winners');
  });

  it('measures a screen by the pinned stage when it has a height', () => {
    const { container } = render(<CountStory />);
    const stage = container.querySelector('section > div') as HTMLElement;
    Object.defineProperty(stage, 'clientHeight', { configurable: true, value: 500 });
    // The stage pins under the navbar: the count starts that gap before the track's top.
    scroll.set(500 * 2.05 - (H - 500));
    settle();
    expect(svg()).toHaveAttribute('aria-label', 'Plurality: Bob elected with 45');
  });

  it('jumps from chapter end to chapter end under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    render(<CountStory />);
    scroll.set(1.6 * H);
    let ran = 0;
    act(() => {
      ran = frames.flush();
    });
    expect(ran).toBe(1);
    expect(svg()).toHaveAttribute('aria-label', 'Plurality: Bob elected with 45');
  });

  it('plays the count to the end, then starts over', () => {
    render(<CountStory />);
    settle();
    const play = screen.getByTestId('home-count-play');
    fireEvent.click(play);
    expect(play).toHaveAccessibleName('Pause the count');
    settle();
    expect(scroll.get()).toBe(5 * H);
    expect(play).toHaveAccessibleName('Play the count');
    fireEvent.click(play);
    expect(scroll.scrollTo).toHaveBeenCalledWith(0, 0);
    fireEvent.click(play);
    expect(play).toHaveAccessibleName('Play the count');
  });

  it('stops playing when the reader takes the wheel', () => {
    render(<CountStory />);
    fireEvent.click(screen.getByTestId('home-count-play'));
    act(() => void frames.flush(3));
    fireEvent.wheel(document.body);
    expect(screen.getByTestId('home-count-play')).toHaveAccessibleName('Play the count');
  });

  it('pauses from the keyboard: a key on the button itself does not stop it first', () => {
    render(<CountStory />);
    const play = screen.getByTestId('home-count-play');
    fireEvent.click(play);
    fireEvent.keyDown(play, { key: ' ' });
    expect(play).toHaveAccessibleName('Pause the count');
    fireEvent.click(play);
    expect(play).toHaveAccessibleName('Play the count');
  });

  it('jumps to a chapter from its tick, smoothly unless motion is reduced', () => {
    render(<CountStory />);
    fireEvent.click(screen.getByTestId('home-count-tick-3'));
    expect(scroll.scrollTo).toHaveBeenLastCalledWith({ top: 3 * H, behavior: 'smooth' });
  });

  it('jumps to a tick at once under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    render(<CountStory />);
    fireEvent.click(screen.getByTestId('home-count-tick-2'));
    expect(scroll.scrollTo).toHaveBeenLastCalledWith({ top: 2 * H, behavior: 'auto' });
  });

  it('stops listening to the page when it leaves', () => {
    const off = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<CountStory />);
    unmount();
    expect(off).toHaveBeenCalledWith('scroll', expect.any(Function));
  });
});
