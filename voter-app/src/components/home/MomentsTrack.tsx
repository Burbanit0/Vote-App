import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useMediaQuery, useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { MOMENTS } from '../playground/MomentRail';
import { clamp01, momentDraw } from '@/lib/home/motion';

// MomentsTrack — the playground's five moments as a horizontal track: on a desktop
// the section pins and scrolling down slides the panels sideways, each numeral rising
// and its line drawing appearing as it arrives. On a phone, or with reduced motion,
// it is a plain list, everything drawn.

/** One stroke drawing per moment, in a 160 × 100 box. */
const GLYPH: Record<string, string> = {
  electorate:
    'M10 50H150M80 8V92M36 34a4 4 0 1 0 8 0a4 4 0 1 0-8 0M52 26a4 4 0 1 0 8 0a4 4 0 1 0-8 0M46 44a4 4 0 1 0 8 0a4 4 0 1 0-8 0M108 62a4 4 0 1 0 8 0a4 4 0 1 0-8 0M122 72a4 4 0 1 0 8 0a4 4 0 1 0-8 0',
  method: 'M50 8H96L112 24V92H50ZM96 8V24H112M62 44H100M62 58H92M62 72H84',
  strategy:
    'M22 72a8 8 0 1 0 16 0a8 8 0 1 0-16 0M122 72a8 8 0 1 0 16 0a8 8 0 1 0-16 0M72 26a8 8 0 1 0 16 0a8 8 0 1 0-16 0M36 62Q80 2 124 62M118 52l6 10 4-11',
  campaign: 'M16 82C46 82 46 34 76 34S108 74 138 42M132 42a6 6 0 1 0 12 0a6 6 0 1 0-12 0',
  bilan: 'M30 18v64M44 18v64M58 18v64M72 18v64M22 70L82 30M102 18v64M116 18v64M130 18v64',
};

const MomentsTrack: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const wide = useMediaQuery('(min-width: 1024px)');
  const reduce = useReducedMotion();
  const pinned = wide && !reduce;

  const track = useRef<HTMLElement>(null);
  const row = useRef<HTMLDivElement>(null);
  const glyphs = useRef<(SVGPathElement | null)[]>([]);
  const numerals = useRef<(HTMLSpanElement | null)[]>([]);

  const kick = useFrameLoop(() => {
    const el = track.current!;
    const H = window.innerHeight;
    const progress =
      (window.scrollY - (el.getBoundingClientRect().top + window.scrollY)) /
      Math.max(1, el.offsetHeight - H);
    const slide = Math.max(0, row.current!.scrollWidth - el.clientWidth);
    row.current!.style.transform = `translateX(${(-Math.min(1, Math.max(0, progress)) * slide).toFixed(1)}px)`;
    glyphs.current.forEach((g, i) => {
      const d = momentDraw(progress, i);
      g!.style.strokeDashoffset = (1 - d).toFixed(3);
      numerals.current[i]!.style.transform = d > 0 ? 'none' : 'translateY(100%)';
    });
    return false;
  });

  // Tabbing to a panel still off to the side: scroll the page to where the track
  // shows it (the sticky box clips rather than scrolls, so focus can't shift it).
  const onFocus = (e: React.FocusEvent) => {
    if (!pinned) return;
    const el = track.current!;
    const panel = (e.target as HTMLElement).closest('article')!;
    const slide = Math.max(1, row.current!.scrollWidth - el.clientWidth);
    const p = clamp01(panel.offsetLeft / slide);
    window.scrollTo({
      top:
        el.getBoundingClientRect().top +
        window.scrollY +
        p * (el.offsetHeight - window.innerHeight),
      behavior: 'auto',
    });
  };

  useEffect(() => {
    if (!pinned) return;
    kick();
    window.addEventListener('scroll', kick, { passive: true });
    window.addEventListener('resize', kick);
    return () => {
      window.removeEventListener('scroll', kick);
      window.removeEventListener('resize', kick);
    };
  }, [pinned, kick]);

  return (
    <section
      ref={track}
      id="home-moments"
      data-testid="home-moments"
      aria-labelledby="home-moments-title"
      className={cn('relative border-t border-border', pinned && 'h-[400vh]')}
    >
      <div
        className={cn(
          pinned
            ? 'sticky top-[49px] flex h-[calc(100dvh-49px)] items-center overflow-clip'
            : 'py-14'
        )}
      >
        <div
          ref={row}
          onFocus={onFocus}
          // Under reduced motion or on a phone the style is never written: no slide.
          style={pinned ? undefined : { transform: 'none' }}
          className={cn(
            'flex gap-9 px-4',
            pinned
              ? 'items-stretch gap-14 pr-[8vw] pl-[6vw] will-change-transform'
              : 'flex-col sm:flex-row sm:flex-wrap'
          )}
        >
          <div className="flex min-w-0 flex-[0_0_min(440px,100%)] flex-col justify-center gap-4">
            <h2
              id="home-moments-title"
              className="font-display text-5xl leading-[0.92] font-extrabold lg:text-7xl"
            >
              {t('home.momentsTitle')}
            </h2>
            <p className="max-w-[26rem] text-lg text-muted-foreground">{t('home.momentsLede')}</p>
          </div>
          {MOMENTS.map((m, i) => (
            <article
              key={m.id}
              className="flex min-w-0 flex-[0_0_min(440px,100%)] flex-col gap-4 border-t-2 border-primary pt-4"
            >
              <div className="flex items-start justify-between gap-4">
                <span className="block h-28 overflow-hidden">
                  <span
                    ref={(el) => {
                      numerals.current[i] = el;
                    }}
                    className="block font-display text-[112px] leading-none font-extrabold text-primary transition-transform duration-500 ease-[cubic-bezier(.2,.7,.2,1)]"
                    style={{ transform: pinned ? 'translateY(100%)' : 'none' }}
                  >
                    {m.n}
                  </span>
                </span>
                <svg viewBox="0 0 160 100" aria-hidden="true" className="h-auto w-48 max-w-[50%]">
                  <path
                    ref={(el) => {
                      glyphs.current[i] = el;
                    }}
                    d={GLYPH[m.id]}
                    pathLength={1}
                    fill="none"
                    className="stroke-foreground"
                    strokeWidth={2.4}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ strokeDasharray: '1 1', strokeDashoffset: pinned ? 1 : 0 }}
                  />
                </svg>
              </div>
              <h3 className="font-sans text-[26px] font-bold tracking-normal">
                <Link to="/playground" className="text-foreground">
                  {tp(`moments.${m.id}.label`)}
                </Link>
              </h3>
              <p className="text-lg text-muted-foreground">{tp(`moments.${m.id}.hint`)}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default MomentsTrack;
