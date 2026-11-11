import React from 'react';
import { act, render } from '@testing-library/react';
import { Fish, Pizza, Soup } from 'lucide-react';
import { fakeMedia } from '@/test/frames';
import DiscoverVoteAnimation from '../DiscoverVoteAnimation';

const FOODS = [
  { Icon: Pizza, name: 'Pizza', color: '#C8352B' },
  { Icon: Fish, name: 'Sushi', color: '#2F5BD3' },
  { Icon: Soup, name: 'Thaï', color: '#1E8A4C' },
];
const realMatchMedia = window.matchMedia;

afterEach(() => {
  window.matchMedia = realMatchMedia;
  vi.useRealTimers();
});

describe('DiscoverVoteAnimation', () => {
  it('draws each stroke in turn, and the eliminated pile drifts off undrawn', () => {
    vi.useFakeTimers();
    fakeMedia({});
    const { container } = render(<DiscoverVoteAnimation rule="two_round" foods={FOODS} />);
    // First round: Pizza's five strokes are drawn 45 ms apart.
    const delays = [...container.querySelectorAll('.stroke-draw')]
      .slice(0, 5)
      .map((l) => (l as SVGElement).style.animationDelay);
    expect(delays).toEqual(['0ms', '45ms', '90ms', '135ms', '180ms']);

    act(() => vi.advanceTimersByTime(1600));
    const drifting = container.querySelector('.tally-migrate-anim')!;
    expect(drifting.querySelectorAll('line').length).toBeGreaterThan(0);
    expect(drifting.querySelector('.stroke-draw')).toBeNull();
  });

  it('under reduced motion, shows the final count with nothing to draw', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    const { container } = render(<DiscoverVoteAnimation rule="two_round" foods={FOODS} />);
    expect(container.querySelectorAll('line').length).toBeGreaterThan(0);
    expect(container.querySelector('.stroke-draw, .home-up')).toBeNull();
  });
});
