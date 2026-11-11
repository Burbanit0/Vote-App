import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SectionRail, { SECTIONS } from '../SectionRail';
import { fakeMedia, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
let tops: Record<string, number>;
const into = vi.fn();

beforeEach(() => {
  fakeMedia({});
  tops = {};
  SECTIONS.forEach(([id], i) => {
    const el = document.createElement('section');
    el.id = id;
    tops[id] = i * 1000;
    el.getBoundingClientRect = () => ({ top: tops[id] }) as DOMRect;
    el.scrollIntoView = into;
    document.body.appendChild(el);
  });
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

describe('SectionRail', () => {
  it('marks the section under the reading line as the page scrolls', () => {
    const frames = manualFrames();
    render(<SectionRail />);
    act(() => void frames.flush());
    expect(screen.getByRole('button', { name: 'Top' })).toHaveAttribute('aria-current', 'true');
    SECTIONS.forEach(([id]) => (tops[id] -= 2000));
    fireEvent.scroll(window);
    act(() => void frames.flush());
    expect(screen.getByRole('button', { name: 'Five moments' })).toHaveAttribute(
      'aria-current',
      'true'
    );
    expect(screen.getByRole('button', { name: 'Top' })).not.toHaveAttribute('aria-current');
  });

  it('jumps to a section, smoothly unless motion is reduced', () => {
    const { unmount } = render(<SectionRail />);
    fireEvent.click(screen.getByRole('button', { name: 'Stories' }));
    expect(into).toHaveBeenLastCalledWith({ behavior: 'smooth' });
    unmount();
    fakeMedia({ 'prefers-reduced-motion': true });
    render(<SectionRail />);
    fireEvent.click(screen.getByRole('button', { name: 'Your turn' }));
    expect(into).toHaveBeenLastCalledWith({ behavior: 'auto' });
  });
});
