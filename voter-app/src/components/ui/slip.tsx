import * as React from 'react';

import { cn } from '@/lib/utils';
import { useReveal } from '@/hooks/useReveal';

/**
 * A ballot slip: a card with its top-right corner folded over, the logo's shape. The
 * clip-path cuts the corner (and its border) off; the fold is drawn back in.
 */
export function Slip({
  fold = 22,
  className,
  style,
  children,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { fold?: number }) {
  return (
    <div
      {...rest}
      className={cn('relative border border-border bg-card', className)}
      style={{
        clipPath: `polygon(0 0, calc(100% - ${fold}px) 0, 100% ${fold}px, 100% 100%, 0 100%)`,
        ...style,
      }}
    >
      {children}
      <span
        aria-hidden
        className="absolute top-0 right-0 bg-border [clip-path:polygon(0_0,100%_100%,0_100%)]"
        style={{ width: fold, height: fold }}
      />
    </div>
  );
}

/**
 * A folded corner drawn over a card instead of cut out of it: for a card that must not
 * clip what it holds (popovers, chart tooltips). The page's colour hides the corner,
 * the fold is drawn beneath it. `surface` is the colour the card sits on.
 */
export function FoldedCorner({ size = 22, surface = 'bg-background' }) {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute -top-px -right-px z-10"
      style={{ width: size + 1, height: size + 1 }}
    >
      <span className={cn('absolute inset-0 [clip-path:polygon(0_0,100%_0,100%_100%)]', surface)} />
      <span className="absolute inset-0 bg-border [clip-path:polygon(0_0,100%_100%,0_100%)]" />
    </span>
  );
}

/** Text whose words rise in turn out of their own masks, from `delay` ms (home-rise). */
export function RiseWords({ text, delay = 0 }: { text: string; delay?: number }) {
  return text.split(' ').map((word, i) => (
    <React.Fragment key={i}>
      {i > 0 && ' '}
      <span className="-mb-[0.08em] inline-block overflow-hidden pb-[0.08em] align-bottom">
        <span className="home-rise inline-block" style={{ animationDelay: `${delay + i * 45}ms` }}>
          {word}
        </span>
      </span>
    </React.Fragment>
  ));
}

/** A section whose entrance animations wait, paused, until it first comes into view. */
export function RevealSection(props: React.HTMLAttributes<HTMLElement>) {
  return <section data-reveal ref={useReveal<HTMLElement>()} {...props} />;
}
