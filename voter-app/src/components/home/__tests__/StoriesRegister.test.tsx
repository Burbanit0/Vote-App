import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StoriesRegister, { figureOf } from '../StoriesRegister';
import { STORIES } from '@/lib/stories';
import { fakeMedia, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
let frames: ReturnType<typeof manualFrames>;
beforeEach(() => {
  fakeMedia({});
  frames = manualFrames();
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  vi.restoreAllMocks();
});

const renderList = () =>
  render(
    <MemoryRouter>
      <StoriesRegister />
    </MemoryRouter>
  );
const rows = () => screen.getAllByRole('listitem');
const slip = () => screen.getByTestId('home-story-slip');
const card = () => slip().firstElementChild as HTMLElement;
const byId = (id: string) => STORIES.findIndex((s) => s.id === id);
/** jsdom never matches :focus-visible on its own: say this focus came from a key. */
const keyboardFocus = (el: HTMLElement) => {
  vi.spyOn(el, 'matches').mockReturnValue(true);
  fireEvent.focus(el);
};

describe('StoriesRegister', () => {
  it('sketches each story by its kind of paradox', () => {
    expect(figureOf(STORIES[byId('spoiler')])).toBe('split');
    expect(figureOf(STORIES[byId('squeeze')])).toBe('center');
    expect(figureOf(STORIES[byId('seuil')])).toBe('arc');
  });

  it('follows a mouse over the list, and hides when it leaves', () => {
    renderList();
    expect(card()).toHaveStyle({ opacity: '0' });
    fireEvent.pointerEnter(rows()[0], { pointerType: 'mouse', clientX: 100, clientY: 300 });
    act(() => void frames.flush());
    expect(card()).toHaveStyle({ opacity: '1', transform: 'rotate(-3deg)' });
    expect(slip().style.transform).toBe('translate3d(122.0px, 150.0px, 0)');
    fireEvent.pointerMove(screen.getByRole('list'), { clientX: 200, clientY: 400 });
    act(() => void frames.flush());
    expect(slip().style.transform).toBe('translate3d(222.0px, 250.0px, 0)');
    fireEvent.pointerEnter(rows()[1], { pointerType: 'mouse', clientX: 200, clientY: 400 });
    expect(card()).toHaveStyle({ transform: 'rotate(2deg)' });
    fireEvent.pointerLeave(screen.getByRole('list'));
    expect(card()).toHaveStyle({ opacity: '0' });
    frames.flush();
    fireEvent.pointerMove(screen.getByRole('list'), { clientX: 0, clientY: 0 });
    expect(frames.pending()).toBe(0);
  });

  it('leaves the slip under the mouse when a click focuses a row', () => {
    renderList();
    const link = screen.getAllByRole('link')[0];
    vi.spyOn(link, 'matches').mockReturnValue(false);
    fireEvent.pointerEnter(rows()[0], { pointerType: 'mouse', clientX: 100, clientY: 300 });
    act(() => void frames.flush());
    fireEvent.focus(link);
    expect(slip().style.transform).toBe('translate3d(122.0px, 150.0px, 0)');
    fireEvent.blur(link);
    expect(card()).toHaveStyle({ opacity: '1' });
  });

  it('ignores a finger', () => {
    renderList();
    fireEvent.pointerEnter(rows()[0], { pointerType: 'touch' });
    expect(card()).toHaveStyle({ opacity: '0' });
  });

  it('shows the slip beside a row focused from the keyboard, then hides it on blur', () => {
    renderList();
    const link = screen.getAllByRole('link')[byId('seuil')];
    keyboardFocus(link);
    expect(card()).toHaveStyle({ opacity: '1' });
    expect(slip().querySelectorAll('circle')).toHaveLength(27);
    fireEvent.blur(link);
    expect(card()).toHaveStyle({ opacity: '0' });
  });

  it('draws the centre sketch for a centre story', () => {
    renderList();
    keyboardFocus(screen.getAllByRole('link')[byId('squeeze')]);
    expect(slip().querySelector('circle[stroke-dasharray]')).not.toBeNull();
  });

  it('jumps straight to the pointer under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    renderList();
    fireEvent.pointerEnter(rows()[0], { pointerType: 'mouse', clientX: 0, clientY: 0 });
    fireEvent.pointerMove(screen.getByRole('list'), { clientX: 300, clientY: 300 });
    let ran = 0;
    act(() => {
      ran = frames.flush();
    });
    expect(ran).toBe(1);
  });
});
