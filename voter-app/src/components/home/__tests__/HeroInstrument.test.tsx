import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HeroInstrument from '../HeroInstrument';
import type { RuleId } from '@/lib/home/scenario';
import { fakeMedia, manualFrames } from '../../../test/frames';

const realMatchMedia = window.matchMedia;
const realAnimate = Element.prototype.animate;

beforeEach(() => fakeMedia({}));
afterEach(() => {
  window.matchMedia = realMatchMedia;
  Element.prototype.animate = realAnimate;
  vi.restoreAllMocks();
});

/** The page holds the rule (HomePage); here, a minimal page does. */
function Hero() {
  const [rule, setRule] = React.useState<RuleId>('plurality');
  return <HeroInstrument rule={rule} onRule={setRule} />;
}

const dotFills = (c: HTMLElement) =>
  [...c.querySelectorAll('[data-testid="hero-map"] circle')].map(
    (d) => (d as SVGElement).style.fill
  );

describe('HeroInstrument', () => {
  it('stamps a different winner under each rule, and marks the runoff’s eliminated', () => {
    render(<Hero />);
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Elected: Bob');
    fireEvent.click(screen.getByTestId('hero-rule-runoff'));
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Elected: Alice');
    expect(screen.getByText('Out after round one')).toBeInTheDocument();
    expect(screen.getByTestId('hero-rule-runoff')).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(screen.getByTestId('hero-rule-approval'));
    expect(screen.getByTestId('hero-winner')).toHaveTextContent('Elected: Carol');
    expect(screen.getByText(/The green dots approve Carol/)).toBeInTheDocument();
  });

  it('greys the voters who do not approve the approval winner', () => {
    const { container } = render(<Hero />);
    expect(dotFills(container)).not.toContain('var(--muted-foreground)');
    fireEvent.click(screen.getByTestId('hero-rule-approval'));
    expect(dotFills(container)).toContain('var(--muted-foreground)');
  });

  it('redraws the tally and knocks the tray on a change, never on mount or a re-pick', () => {
    const animate = vi.fn();
    Element.prototype.animate = animate as unknown as typeof Element.prototype.animate;
    render(<Hero />);
    fireEvent.click(screen.getByTestId('hero-rule-plurality'));
    expect(animate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('hero-rule-runoff'));
    const targets = animate.mock.instances as unknown as Element[];
    expect(targets.some((el) => el.tagName === 'path')).toBe(true);
    expect(targets).toContain(screen.getByTestId('hero-instrument'));
  });

  it('survives a browser without the Web Animations API', () => {
    // @ts-expect-error — jsdom-like: no animate()
    delete Element.prototype.animate;
    render(<Hero />);
    expect(() => fireEvent.click(screen.getByTestId('hero-rule-runoff'))).not.toThrow();
  });

  it('keeps still under reduced motion', () => {
    fakeMedia({ 'prefers-reduced-motion': true });
    const animate = vi.fn();
    Element.prototype.animate = animate as unknown as typeof Element.prototype.animate;
    const frames = manualFrames();
    render(<Hero />);
    fireEvent.click(screen.getByTestId('hero-rule-runoff'));
    fireEvent.pointerMove(screen.getByTestId('hero-map'), { pointerType: 'mouse', clientX: 10 });
    expect(animate).not.toHaveBeenCalled();
    expect(frames.pending()).toBe(0);
  });

  it('drifts the map layers with a mouse, not a finger, and settles back', () => {
    const frames = manualFrames();
    const { container } = render(<Hero />);
    const map = screen.getByTestId('hero-map');
    vi.spyOn(map, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      top: 0,
      width: 100,
      height: 70,
    } as DOMRect);
    fireEvent.pointerMove(map, { pointerType: 'touch', clientX: 100, clientY: 70 });
    expect(frames.pending()).toBe(0);
    fireEvent.pointerMove(map, { pointerType: 'mouse', clientX: 100, clientY: 70 });
    act(() => void frames.flush());
    const layers = container.querySelectorAll('[data-testid="hero-map"] svg > g[transform]');
    expect(layers[1].getAttribute('transform')).toBe('translate(0.750 0.750)');
    fireEvent.pointerLeave(map);
    act(() => void frames.flush());
    expect(layers[1].getAttribute('transform')).toBe('translate(0.000 0.000)');
  });
});
