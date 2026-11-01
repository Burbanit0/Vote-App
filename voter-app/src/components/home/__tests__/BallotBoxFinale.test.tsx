import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import BallotBoxFinale from '../BallotBoxFinale';
import { fakeMedia, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
const realIO = window.IntersectionObserver;
let seen: (entries: { isIntersecting: boolean }[]) => void;
const disconnect = vi.fn();

beforeEach(() => {
  fakeMedia({});
  window.IntersectionObserver = class {
    constructor(cb: typeof seen) {
      seen = cb;
    }
    observe() {}
    disconnect = disconnect;
  } as unknown as typeof IntersectionObserver;
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  window.IntersectionObserver = realIO;
  vi.restoreAllMocks();
});

const renderBox = (onOpen = vi.fn()) =>
  render(
    <MemoryRouter>
      <BallotBoxFinale onOpen={onOpen} />
    </MemoryRouter>
  );
const ballots = () =>
  [...screen.getByRole('img').querySelectorAll('rect')].filter((r) => r.getAttribute('rx') === '1');

describe('BallotBoxFinale', () => {
  it('fills the box once, the first time it is seen', () => {
    const frames = manualFrames();
    renderBox();
    act(() => seen([{ isIntersecting: false }]));
    expect(frames.pending()).toBe(0);
    act(() => seen([{ isIntersecting: true }]));
    expect(disconnect).toHaveBeenCalled();
    frames.flush(10);
    expect(ballots().some((b) => b.getAttribute('opacity') === '1')).toBe(true);
    frames.flush();
    expect(frames.pending()).toBe(0);
    expect(ballots().every((b) => b.getAttribute('opacity') === '1')).toBe(true);
  });

  it('shows the full box at once under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    const frames = manualFrames();
    renderBox();
    act(() => seen([{ isIntersecting: true }]));
    expect(frames.pending()).toBe(0);
    expect(ballots().every((b) => b.getAttribute('opacity') === '1')).toBe(true);
  });

  it('opens the instrument', () => {
    const onOpen = vi.fn();
    renderBox(onOpen);
    fireEvent.click(screen.getByRole('button', { name: /open the instrument/i }));
    expect(onOpen).toHaveBeenCalled();
  });
});
