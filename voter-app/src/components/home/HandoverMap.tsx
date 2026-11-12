import React, { useEffect, useRef } from 'react';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { CANDIDATES, VOTERS } from '@/lib/home/scenario';
import { COUNT_IN, HERO_GONE, handoverFrame, handoverProgress } from '@/lib/home/handover';
import { countPin } from './countPin';

// HandoverMap — the hero's map flies into the count's. Between the top of the page and
// the point where the count pins, the page publishes its progress as --handover on
// the homepage root: the hero's text and tray fade out on it, the count's box, piles,
// caption and scrubber fade in on it. Meanwhile this fixed layer draws the map in
// flight between the two maps' live positions, so it leaves the hero exactly where
// the hero drew it and lands exactly where the count draws it. Neither real map shows
// mid-flight, and whatever has faded out is inert (no clicks, no focus). Under reduced
// motion none of this runs: --handover stays unset and both sections stand as they are.

const MUTED = 'var(--muted-foreground)';
/** How much of a screen before the count pins the handover starts (never above the top). */
const RUN = 0.85;

interface Page {
  root: HTMLElement;
  layer: SVGSVGElement;
  from: Element;
  to: Element;
  count: Element;
  stage: Element;
  /** The hero's text and tray, cleared away by the handover. */
  fadingOut: Element[];
  /** The count's controls, brought in by it. */
  fadingIn: Element[];
  /** What the last frame drew for: progress and viewport. */
  last: string;
}

const HandoverMap: React.FC = () => {
  const reduce = useReducedMotion();
  const layer = useRef<SVGSVGElement>(null);
  const card = useRef<SVGRectElement>(null);
  const axes = useRef<(SVGLineElement | null)[]>([]);
  const dots = useRef<(SVGCircleElement | null)[]>([]);
  const greys = useRef<(SVGCircleElement | null)[]>([]);
  const greyLayer = useRef<SVGGElement>(null);
  const cands = useRef<(SVGCircleElement | null)[]>([]);
  const labels = useRef<(SVGTextElement | null)[]>([]);

  /** Draws the map in flight at progress h, between the hero's map and the count's. */
  const fly = (h: number, from: Element, to: Element) => {
    const f = handoverFrame(h, from.getBoundingClientRect(), to.getBoundingClientRect());
    const set = (el: Element, attrs: Record<string, number>) =>
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v.toFixed(2)));
    set(card.current!, {
      x: f.card.x,
      y: f.card.y,
      width: f.card.w,
      height: f.card.h,
      rx: f.card.r,
    });
    const cx = f.card.x + f.card.w / 2;
    const cy = f.card.y + f.card.h / 2;
    set(axes.current[0]!, { x1: f.card.x, y1: cy, x2: f.card.x + f.card.w, y2: cy });
    set(axes.current[1]!, { x1: cx, y1: f.card.y, x2: cx, y2: f.card.y + f.card.h });
    // The voters keep the colours the hero showed them in (its rule may have changed them).
    const heroDots = from.querySelectorAll<SVGCircleElement>('[data-voter]');
    f.voters.forEach((d, i) => {
      set(dots.current[i]!, { cx: d.x, cy: d.y, r: d.r });
      set(greys.current[i]!, { cx: d.x, cy: d.y, r: d.r });
      dots.current[i]!.style.fill = heroDots[i].style.fill;
    });
    layer.current!.style.setProperty('--voter-opacity', f.voterOpacity.toFixed(3));
    greyLayer.current!.setAttribute('opacity', f.grey.toFixed(3));
    f.candidates.forEach((c, i) => {
      set(cands.current[i]!, { cx: c.x, cy: c.y, r: c.r, 'stroke-width': c.r * 0.3 });
      set(labels.current[i]!, { x: c.x, y: c.labelY, 'font-size': c.size });
    });
  };

  /** The page's nodes, found once when the handover starts; null when it is off. */
  const page = useRef<Page | null>(null);

  /** One frame: publish the progress, hide what has faded, fly the map if mid-way. */
  const step = (n: Page) => {
    const end = countPin(n.count, n.stage).top;
    const start = Math.max(0, end - RUN * window.innerHeight);
    // Rounded once, so the CSS fades and the flying layer agree on where the flight is.
    const h = Number(handoverProgress(window.scrollY, start, end).toFixed(4));
    const key = `${h}|${window.innerWidth}|${window.innerHeight}`;
    if (key === n.last) return;
    n.last = key;
    n.root.style.setProperty('--handover', String(h));
    // Faded is gone: no clicks, no focus on what cannot be seen.
    n.fadingOut.forEach((el) => el.toggleAttribute('inert', h >= HERO_GONE));
    n.fadingIn.forEach((el) => el.toggleAttribute('inert', h <= COUNT_IN));
    const flying = h > 0 && h < 1;
    n.layer.style.display = flying ? 'block' : 'none';
    if (flying) fly(h, n.from, n.to);
  };

  const kick = useFrameLoop(() => {
    // A frame already queued when the handover was switched off finds no page.
    if (page.current) step(page.current);
    return false;
  });

  useEffect(() => {
    if (reduce) return;
    const root = document.querySelector<HTMLElement>('[data-home]')!;
    const count = document.getElementById('home-count')!;
    const n: Page = {
      root,
      layer: layer.current!,
      from: root.querySelector('[data-handover-from]')!,
      to: root.querySelector('[data-handover-to]')!,
      count,
      stage: count.firstElementChild!,
      fadingOut: [...root.querySelectorAll('[data-handover-out]')],
      fadingIn: [...root.querySelectorAll('[data-handover-in]')],
      last: '',
    };
    page.current = n;
    kick();
    window.addEventListener('scroll', kick, { passive: true });
    window.addEventListener('resize', kick);
    return () => {
      window.removeEventListener('scroll', kick);
      window.removeEventListener('resize', kick);
      page.current = null;
      root.style.removeProperty('--handover');
      n.layer.style.display = 'none';
      [...n.fadingOut, ...n.fadingIn].forEach((el) => el.removeAttribute('inert'));
    };
  }, [reduce, kick]);

  return (
    <svg
      ref={layer}
      aria-hidden="true"
      data-testid="home-handover"
      className="pointer-events-none fixed inset-0 z-20 h-full w-full"
      style={{ display: 'none' }}
    >
      <rect ref={card} className="fill-card stroke-border" strokeWidth={1.2} />
      <g className="stroke-border" strokeWidth={1}>
        {[0, 1].map((i) => (
          <line
            key={i}
            ref={(el) => {
              axes.current[i] = el;
            }}
          />
        ))}
      </g>
      <g style={{ opacity: 'var(--voter-opacity)' }}>
        {VOTERS.map((_, i) => (
          <circle
            key={i}
            ref={(el) => {
              dots.current[i] = el;
            }}
          />
        ))}
        <g ref={greyLayer} opacity="0">
          {VOTERS.map((_, i) => (
            <circle
              key={i}
              ref={(el) => {
                greys.current[i] = el;
              }}
              style={{ fill: MUTED }}
            />
          ))}
        </g>
      </g>
      {CANDIDATES.map((c, i) => (
        <g key={c.name}>
          <circle
            ref={(el) => {
              cands.current[i] = el;
            }}
            fill={c.color}
            className="stroke-card"
          />
          <text
            ref={(el) => {
              labels.current[i] = el;
            }}
            textAnchor="middle"
            fontWeight={700}
            className="fill-foreground"
          >
            {c.name}
          </text>
        </g>
      ))}
    </svg>
  );
};

export default HandoverMap;
