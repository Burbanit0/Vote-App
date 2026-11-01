import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { EASE, coverPolygon, easeOutCubic, odometer, slipPolygon } from '@/lib/home/motion';

// HomeEntrance — the first look at the homepage, once per session: a counter rolls to
// 100 voters on an ink screen, then the screen folds into the navbar's ballot-slip
// mark and the page is there. It never blocks: the overlay lets clicks through, and
// any click, wheel, touch or key ends it at once. Skipped under reduced motion.

const SEEN_KEY = 'vote-lab:home-entrance';
const COUNT_MS = 1000;
const WIPE_AT = 1150;
const DONE_AT = 2100;
const STRIP = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0];

function seen(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1';
  } catch {
    // Storage blocked: better never to play it than to replay it on every visit.
    return true;
  }
}

function markSeen() {
  try {
    sessionStorage.setItem(SEEN_KEY, '1');
  } catch {
    // Storage blocked: nothing to remember it in.
  }
}

/** Where the brand mark sits, to fold the screen into it. */
function markOrigin(): { x: number; y: number } {
  const mark = document.querySelector('[data-brand-mark]');
  if (!mark) return { x: 16, y: 12 };
  const r = mark.getBoundingClientRect();
  return { x: r.left, y: r.top };
}

type Phase = 'count' | 'wipe' | 'done';

const HomeEntrance: React.FC<{ onReveal: () => void }> = ({ onReveal }) => {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const [phase, setPhase] = useState<Phase>(() => (reduce || seen() ? 'done' : 'count'));
  const digits = useRef<(HTMLSpanElement | null)[]>([]);
  const start = useRef(0);

  const kick = useFrameLoop((now) => {
    // Dismissed mid-count: the digits are gone, and so is the loop.
    if (!digits.current[0]) return false;
    const t = Math.min(1, (now - start.current) / COUNT_MS);
    const v = 100 * easeOutCubic(t);
    digits.current.forEach((el, i) => {
      el!.style.transform = `translateY(${-odometer(v, 2 - i)}em)`;
    });
    return t < 1;
  });

  // The page starts settling in as the screen folds away, not after.
  const revealed = phase !== 'count';
  useEffect(() => {
    if (revealed) onReveal();
  }, [revealed, onReveal]);

  // Keyed on done-ness, not the phase: the timers set at the start run through the wipe.
  const done = phase === 'done';
  useEffect(() => {
    if (done) return;
    markSeen();
    start.current = performance.now();
    kick();
    const finish = () => setPhase('done');
    const timers = [setTimeout(() => setPhase('wipe'), WIPE_AT), setTimeout(finish, DONE_AT)];
    const events = ['pointerdown', 'wheel', 'touchstart', 'keydown'] as const;
    events.forEach((e) => window.addEventListener(e, finish, { passive: true }));
    return () => {
      timers.forEach(clearTimeout);
      events.forEach((e) => window.removeEventListener(e, finish));
    };
  }, [done, kick]);

  if (done) return null;
  const o = markOrigin();
  const clip =
    phase === 'count' ? coverPolygon(window.innerWidth, window.innerHeight) : slipPolygon(o.x, o.y);

  return (
    <div
      aria-hidden="true"
      data-testid="home-entrance"
      data-phase={phase}
      className="pointer-events-none fixed inset-0 z-[60] flex flex-col items-center justify-center gap-3 bg-foreground text-background"
      style={{ clipPath: clip, transition: `clip-path 900ms ${EASE.fold}` }}
    >
      <span
        className="flex font-mono text-[clamp(88px,12vw,168px)] leading-none font-semibold transition-opacity duration-300"
        style={{ opacity: phase === 'count' ? 1 : 0 }}
      >
        {[0, 1, 2].map((col) => (
          <span key={col} className="block h-[1em] overflow-hidden">
            <span
              ref={(el) => {
                digits.current[col] = el;
              }}
              className="flex flex-col"
            >
              {STRIP.map((n, k) => (
                <span key={k} className="block h-[1em]">
                  {n}
                </span>
              ))}
            </span>
          </span>
        ))}
      </span>
      <span
        className="text-lg transition-opacity duration-300"
        style={{ opacity: phase === 'count' ? 0.7 : 0 }}
      >
        {t('home.introVoters')}
      </span>
    </div>
  );
};

export default HomeEntrance;
