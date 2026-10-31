import React from 'react';
import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HandoverMap from '../HandoverMap';
import { VOTERS } from '@/lib/home/scenario';
import { fakeMedia, fakeScroll, manualFrames } from '../../../test/frames';

// The page around the flying map: the homepage root, the hero's map (its voters
// coloured by its rule) and the count's section, its pinned stage and its drawing.
// jsdom lays nothing out, so the boxes are stubbed.
const realMatchMedia = window.matchMedia;
const realScrollTo = window.scrollTo;
let root: HTMLElement;
let heroText: HTMLElement;
let scrubber: HTMLElement;
let scroll: ReturnType<typeof fakeScroll>;
let frames: ReturnType<typeof manualFrames>;
const COUNT_TOP = 1200;
const STAGE = window.innerHeight - 50;

function page() {
  root = document.createElement('div');
  root.setAttribute('data-home', '');
  const from = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  from.setAttribute('data-handover-from', '');
  VOTERS.forEach((_, i) => {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('data-voter', '');
    c.style.fill = i === 0 ? 'rgb(1, 2, 3)' : 'var(--muted-foreground)';
    from.appendChild(c);
  });
  const count = document.createElement('section');
  count.id = 'home-count';
  const stage = document.createElement('div');
  Object.defineProperty(stage, 'clientHeight', { value: STAGE });
  const to = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  to.setAttribute('data-handover-to', '');
  stage.appendChild(to);
  count.appendChild(stage);
  heroText = document.createElement('div');
  heroText.setAttribute('data-handover-out', '');
  scrubber = document.createElement('div');
  scrubber.setAttribute('data-handover-in', '');
  root.append(heroText, from, count, scrubber);
  document.body.appendChild(root);
  const box = (top: number, height: number) => ({ left: 0, top, width: 1000, height }) as DOMRect;
  from.getBoundingClientRect = () => box(100 - scroll.get(), 700);
  to.getBoundingClientRect = () => box(COUNT_TOP + 300 - scroll.get(), 550);
  count.getBoundingClientRect = () => box(COUNT_TOP - scroll.get(), 6000);
}

beforeEach(() => {
  fakeMedia({});
  frames = manualFrames();
  scroll = fakeScroll(0);
  page();
});
afterEach(() => {
  window.matchMedia = realMatchMedia;
  window.scrollTo = realScrollTo;
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

const handover = () => root.style.getPropertyValue('--handover');
const layer = () => screen.getByTestId('home-handover');
// The count pins at its top less the navbar gap; the handover runs over the 0.85 screen before.
const END = COUNT_TOP - (window.innerHeight - STAGE);
const START = END - 0.85 * window.innerHeight;

describe('HandoverMap', () => {
  it('stays out of sight at the top of the page and once the count has pinned', () => {
    render(<HandoverMap />, { container: root.appendChild(document.createElement('div')) });
    act(() => void frames.flush());
    expect(handover()).toBe('0');
    expect(layer()).toHaveStyle({ display: 'none' });
    // At the top, the hero is live and the count's controls are not reachable yet.
    expect(heroText).not.toHaveAttribute('inert');
    expect(scrubber).toHaveAttribute('inert');
    scroll.set(END + 10);
    act(() => void frames.flush());
    expect(handover()).toBe('1');
    expect(layer()).toHaveStyle({ display: 'none' });
    expect(heroText).toHaveAttribute('inert');
    expect(scrubber).not.toHaveAttribute('inert');
  });

  it('flies the map mid-way, keeping the colours the hero gave the voters', () => {
    render(<HandoverMap />, { container: root.appendChild(document.createElement('div')) });
    scroll.set((START + END) / 2);
    act(() => void frames.flush());
    expect(handover()).toBe('0.5');
    expect(layer()).toHaveStyle({ display: 'block' });
    const dots = layer().querySelectorAll('circle');
    expect((dots[0] as SVGCircleElement).style.fill).toBe('rgb(1, 2, 3)');
    expect(Number(dots[0].getAttribute('r'))).toBeGreaterThan(0);
    expect(layer().querySelector('rect')!.getAttribute('width')).not.toBeNull();
    expect(layer().querySelector('text')!.getAttribute('font-size')).not.toBeNull();
  });

  it('redraws nothing when a scroll moves nothing', () => {
    render(<HandoverMap />, { container: root.appendChild(document.createElement('div')) });
    scroll.set((START + END) / 2);
    act(() => void frames.flush());
    const card = layer().querySelector('rect')!;
    const setAttribute = vi.spyOn(card, 'setAttribute');
    scroll.set((START + END) / 2);
    act(() => void frames.flush());
    expect(setAttribute).not.toHaveBeenCalled();
  });

  it('does nothing under reduced motion: both sections stand as they are', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    render(<HandoverMap />, { container: root.appendChild(document.createElement('div')) });
    expect(frames.pending()).toBe(0);
    expect(handover()).toBe('');
  });

  it('clears its progress and listeners when it leaves', () => {
    const off = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<HandoverMap />, {
      container: root.appendChild(document.createElement('div')),
    });
    scroll.set((START + END) / 2);
    act(() => void frames.flush());
    expect(layer()).toHaveStyle({ display: 'block' });
    const shown = layer();
    // A frame queued just before it leaves must not bring the handover back.
    scroll.set(END - 1);
    unmount();
    act(() => void frames.flush());
    expect(handover()).toBe('');
    expect(shown).toHaveStyle({ display: 'none' });
    expect(heroText).not.toHaveAttribute('inert');
    expect(scrubber).not.toHaveAttribute('inert');
    expect(off).toHaveBeenCalledWith('scroll', expect.any(Function));
  });
});
