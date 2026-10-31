import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';

// Aceternity "card-hover-effect" (via the shadcn MCP, @aceternity registry),
// reduced to its one idea: a halo that slides from card to card. Upstream ships
// a whole <a href> grid with its own card styling; here the caller keeps its own
// cards and this only adds the halo behind them. Every halo in one list shares
// `layoutId`, which is what makes motion glide it between items instead of
// fading one out and the next in. The hover state lives here, not in the page,
// so a hover re-renders this list and nothing around it.

export const HaloList: React.FC<{
  as: 'ol' | 'ul';
  className?: string;
  layoutId: string;
  items: { key: string; node: React.ReactNode }[];
}> = ({ as: Tag, className, layoutId, items }) => {
  const [hovered, setHovered] = useState<string | null>(null);
  return (
    <Tag className={className} onMouseLeave={() => setHovered(null)}>
      {items.map(({ key, node }) => (
        // Decorative only: the interactive element is the caller's link inside,
        // whose focus bubbles here, so keyboard users get the same halo.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
        <li
          key={key}
          className="relative"
          onMouseEnter={() => setHovered(key)}
          onFocus={() => setHovered(key)}
          onBlur={() => setHovered(null)}
        >
          <AnimatePresence>
            {hovered === key && (
              <motion.span
                aria-hidden
                layoutId={layoutId}
                className="pointer-events-none absolute -inset-1 block rounded-xl bg-primary/15"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1, transition: { duration: 0.15 } }}
                exit={{ opacity: 0, transition: { duration: 0.15, delay: 0.2 } }}
              />
            )}
          </AnimatePresence>
          <div className="relative h-full">{node}</div>
        </li>
      ))}
    </Tag>
  );
};
