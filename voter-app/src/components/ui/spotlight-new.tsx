import React from 'react';

// Aceternity "spotlight-new" (via the shadcn MCP, @aceternity registry): two
// slow-drifting light cones. Tinted with the theme's --primary instead of the
// upstream hard-coded blue, so it follows light/dark; the drift is the CSS
// `.spotlight-drift` (styles/tailwind.css), not upstream's JS loop, and stops
// under prefers-reduced-motion (the visual e2e config forces it).

const tint = (pct: number) => `color-mix(in oklab, var(--primary) ${pct}%, transparent)`;
const FIRST = `radial-gradient(68.54% 68.72% at 55.02% 31.46%, ${tint(14)} 0, ${tint(4)} 50%, transparent 80%)`;
const SECOND = `radial-gradient(50% 50% at 50% 50%, ${tint(10)} 0, ${tint(3)} 80%, transparent 100%)`;
const THIRD = `radial-gradient(50% 50% at 50% 50%, ${tint(7)} 0, ${tint(3)} 80%, transparent 100%)`;

const HEIGHT = 1380;
const SMALL_WIDTH = 240;

const Cone: React.FC<{ side: 'left' | 'right' }> = ({ side }) => {
  const s = side === 'left' ? 1 : -1;
  const at = side === 'left' ? 'left-0' : 'right-0';
  const origin = side === 'left' ? 'origin-top-left' : 'origin-top-right';
  return (
    <div
      className={`spotlight-drift absolute top-0 ${at} h-full w-full`}
      style={{ '--drift': `${s * 100}px` } as React.CSSProperties}
    >
      <div
        style={{
          transform: `translateY(-350px) rotate(${s * -45}deg)`,
          background: FIRST,
          width: 560,
          height: HEIGHT,
        }}
        className={`absolute top-0 ${at}`}
      />
      <div
        style={{
          transform: `rotate(${s * -45}deg) translate(${s * 5}%, -50%)`,
          background: SECOND,
          width: SMALL_WIDTH,
          height: HEIGHT,
        }}
        className={`absolute top-0 ${at} ${origin}`}
      />
      <div
        style={{
          transform: `rotate(${s * -45}deg) translate(${s * -180}%, -70%)`,
          background: THIRD,
          width: SMALL_WIDTH,
          height: HEIGHT,
        }}
        className={`absolute top-0 ${at} ${origin}`}
      />
    </div>
  );
};

export const Spotlight: React.FC = () => (
  <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
    <Cone side="left" />
    <Cone side="right" />
  </div>
);
