import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';

// SectionRail — five ticks pinned to the right edge of the homepage (desktop only):
// where you are on a long page, and a jump to any section.

export const SECTIONS = [
  ['home-top', 'home.sectionTop'],
  ['home-count', 'home.sectionCount'],
  ['home-moments', 'home.sectionMoments'],
  ['home-stories', 'home.sectionStories'],
  ['home-turn', 'home.sectionTurn'],
] as const;

const SectionRail: React.FC = () => {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const [current, setCurrent] = useState(0);

  const kick = useFrameLoop(() => {
    const line = window.innerHeight * 0.4;
    setCurrent(
      SECTIONS.reduce(
        (c, [id], i) => (document.getElementById(id)!.getBoundingClientRect().top <= line ? i : c),
        0
      )
    );
    return false;
  });

  useEffect(() => {
    kick();
    window.addEventListener('scroll', kick, { passive: true });
    return () => window.removeEventListener('scroll', kick);
  }, [kick]);

  return (
    <nav
      aria-label={t('home.sections')}
      className="fixed top-1/2 right-3 z-30 hidden -translate-y-1/2 flex-col gap-0.5 lg:flex"
    >
      {SECTIONS.map(([id, key], i) => (
        <button
          key={id}
          type="button"
          aria-label={t(key)}
          aria-current={i === current ? 'true' : undefined}
          onClick={() =>
            document.getElementById(id)!.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' })
          }
          className="flex h-11 w-11 items-center justify-center"
        >
          <span
            className={cn(
              'block w-1 rounded-sm transition-[height,background-color] duration-[240ms]',
              i === current ? 'h-7 bg-primary' : 'h-3 bg-muted-foreground/50'
            )}
          />
        </button>
      ))}
    </nav>
  );
};

export default SectionRail;
