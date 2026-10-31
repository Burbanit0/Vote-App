import React from 'react';
import { motion, useMotionTemplate, useMotionValue, useReducedMotion } from 'motion/react';
import { cn } from '@/lib/utils';

// Aceternity "hero-highlight" (via the shadcn MCP, @aceternity registry): a dot
// grid whose dots light up in a halo around the pointer, and a marker-pen
// highlight that sweeps under a phrase. Upstream draws the dots as four SVG
// data-URIs (light/dark x idle/hover); here they are CSS radial-gradients on the
// theme tokens, so one layer per state follows the theme on its own.

const dots = (color: string) => `radial-gradient(${color} 1.2px, transparent 1.4px)`;

export const HeroHighlight: React.FC<{
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
}> = ({ children, className, containerClassName }) => {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const mask = useMotionTemplate`radial-gradient(200px circle at ${mouseX}px ${mouseY}px, black 0%, transparent 100%)`;

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent<HTMLDivElement>) {
    const { left, top } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
  }

  return (
    <div className={cn('group relative', containerClassName)} onMouseMove={handleMouseMove}>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[length:16px_16px]"
        style={{ backgroundImage: dots('var(--border)') }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[length:16px_16px] opacity-0 transition duration-300 group-hover:opacity-100"
        style={{
          backgroundImage: dots('var(--primary)'),
          WebkitMaskImage: mask,
          maskImage: mask,
        }}
      />
      <div className={cn('relative', className)}>{children}</div>
    </div>
  );
};

export const Highlight: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => {
  const reduce = useReducedMotion();
  return (
    <motion.span
      initial={reduce ? false : { backgroundSize: '0% 100%' }}
      animate={{ backgroundSize: '100% 100%' }}
      transition={{ duration: 2, ease: 'linear', delay: 0.5 }}
      style={{ backgroundRepeat: 'no-repeat', backgroundPosition: 'left center' }}
      className={cn(
        'box-decoration-clone rounded-lg bg-gradient-to-r from-primary/15 to-primary/30 px-1 pb-1',
        className
      )}
    >
      {children}
    </motion.span>
  );
};
