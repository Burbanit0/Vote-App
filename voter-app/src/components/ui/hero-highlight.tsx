import React from 'react';
import { cn } from '@/lib/utils';

// Aceternity "hero-highlight" (via the shadcn MCP, @aceternity registry): a dot
// grid whose dots light up in a halo around the pointer, and a marker-pen
// highlight that sweeps under a phrase. Upstream draws the dots as four SVG
// data-URIs (light/dark x idle/hover) and tracks the pointer in motion values;
// here the dots are CSS radial-gradients on the theme tokens and the pointer is
// two CSS variables, so a mouse move re-renders nothing.

const dots = (color: string) => `radial-gradient(${color} 1.2px, transparent 1.4px)`;
const MASK = 'radial-gradient(200px circle at var(--hx) var(--hy), black 0%, transparent 100%)';

export const HeroHighlight: React.FC<{
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
}> = ({ children, className, containerClassName }) => {
  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent<HTMLDivElement>) {
    const { left, top } = currentTarget.getBoundingClientRect();
    currentTarget.style.setProperty('--hx', `${clientX - left}px`);
    currentTarget.style.setProperty('--hy', `${clientY - top}px`);
  }

  // A named group: an unnamed `group` here would also fire every `group-hover:`
  // inside the hero (HeroInstrument has its own) whenever the hero is hovered.
  return (
    <div
      data-testid="hero-highlight"
      className={cn('group/hero relative', containerClassName)}
      onMouseMove={handleMouseMove}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[length:16px_16px]"
        style={{ backgroundImage: dots('var(--border)') }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[length:16px_16px] opacity-0 transition duration-300 group-hover/hero:opacity-100 motion-reduce:transition-none"
        style={{ backgroundImage: dots('var(--primary)'), WebkitMaskImage: MASK, maskImage: MASK }}
      />
      <div className={cn('relative', className)}>{children}</div>
    </div>
  );
};

export const Highlight: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <span
    style={{ backgroundRepeat: 'no-repeat', backgroundPosition: 'left center' }}
    className={cn(
      'highlight-sweep box-decoration-clone rounded-lg bg-gradient-to-r from-primary/15 to-primary/30 px-1 pb-1',
      className
    )}
  >
    {children}
  </span>
);
