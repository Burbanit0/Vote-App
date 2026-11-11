import React, { useRef, useState } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { approach } from '@/lib/home/motion';
import { STORIES, type Story } from '@/lib/stories';
import { CANDIDATES } from '@/lib/home/scenario';

// StoriesRegister — the guided stories as a register (a ruled list, like the lines
// of an electoral roll). With a mouse, a ballot slip follows the pointer over the
// list and sketches the story's paradox; keyboard focus shows it beside the row.
// Touch screens never see it (the slip is hidden on coarse pointers).

type Figure = 'split' | 'center' | 'arc';
/** Stories about a vote that splits; the parliament ones draw a hemicycle; the rest a centre. */
const SPLIT = new Set(['spoiler', 'utile', 'five', 'clones', 'renversement']);
export function figureOf(s: Story): Figure {
  if (s.mode === 'parliament') return 'arc';
  return SPLIT.has(s.id) ? 'split' : 'center';
}

/** Alice's, Carol's and Bob's colours, as everywhere on the page. */
const BLOCS = CANDIDATES.map((c) => c.color);

/** A 27-seat hemicycle: three rows, left to right in three blocs. */
const SEATS = [
  [7, 34],
  [9, 52],
  [11, 70],
]
  .flatMap(([n, r]) =>
    Array.from({ length: n }, (_, j) => {
      const a = Math.PI * (1 - j / (n - 1));
      return { x: 90 + Math.cos(a) * r, y: 76 - Math.sin(a) * r };
    })
  )
  .sort((a, b) => a.x - b.x)
  // Left to right: 11 seats for Alice's bloc, 4 for Carol's, 12 for Bob's.
  .map((s, j) => ({ ...s, c: BLOCS[Number(j >= 11) + Number(j >= 15)] }));

const GROUND = <line x1={8} y1={60} x2={172} y2={60} className="stroke-border" />;
const SKETCH: Record<Figure, React.ReactNode> = {
  arc: SEATS.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={5} fill={s.c} />),
  // The left splits, and the right wins: the spoiler's shape.
  split: (
    <>
      {GROUND}
      <circle cx={46} cy={44} r={9} fill={BLOCS[0]} />
      <circle cx={68} cy={48} r={9} fill={BLOCS[1]} />
      <circle
        cx={138}
        cy={42}
        r={11}
        fill={BLOCS[2]}
        className="stroke-ballot-stamp"
        strokeWidth={2.5}
      />
    </>
  ),
  // The candidate in the middle, acceptable to both sides.
  center: (
    <>
      {GROUND}
      <circle cx={36} cy={46} r={9} fill={BLOCS[0]} />
      <circle cx={90} cy={46} r={7} fill={BLOCS[1]} />
      <circle
        cx={90}
        cy={46}
        r={16}
        fill="none"
        stroke={BLOCS[1]}
        strokeWidth={1.5}
        strokeDasharray="3 3"
      />
      <circle cx={144} cy={46} r={9} fill={BLOCS[2]} />
    </>
  ),
};

const Sketch: React.FC<{ figure: Figure }> = ({ figure }) => (
  <svg viewBox="0 0 180 80" width="200" height="89" aria-hidden="true" className="block">
    {SKETCH[figure]}
  </svg>
);

const StoriesRegister: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const reduce = useReducedMotion();
  const [hover, setHover] = useState(-1);
  const slip = useRef<HTMLDivElement>(null);
  const pos = useRef({ x: 0, y: 0, tx: 0, ty: 0 });

  const kick = useFrameLoop(() => {
    const p = pos.current;
    const k = reduce ? 1 : 0.18;
    p.x = approach(p.x, p.tx, k, 0.3);
    p.y = approach(p.y, p.ty, k, 0.3);
    slip.current!.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
    return p.x !== p.tx || p.y !== p.ty;
  });

  /** Aim the slip at a point; the first time it appears, it jumps there. */
  const aim = (x: number, y: number, jump: boolean) => {
    const p = pos.current;
    p.tx = x;
    p.ty = y;
    if (jump) {
      p.x = x;
      p.y = y;
    }
    kick();
  };

  const onEnter = (i: number) => (e: React.PointerEvent) => {
    if (e.pointerType === 'touch') return;
    aim(e.clientX + 22, e.clientY - 150, hover < 0);
    setHover(i);
  };
  const onMove = (e: React.PointerEvent) => {
    if (hover >= 0) aim(e.clientX + 22, e.clientY - 150, false);
  };
  // Only keyboard focus places the slip: a mouse click also focuses the link, and
  // must leave the slip under the pointer.
  const keyboard = useRef(false);
  const onFocus = (i: number) => (e: React.FocusEvent<HTMLAnchorElement>) => {
    keyboard.current = e.currentTarget.matches(':focus-visible');
    if (!keyboard.current) return;
    const r = e.currentTarget.getBoundingClientRect();
    aim(r.right - 300, r.top - 120, true);
    setHover(i);
  };
  const leave = () => setHover(-1);
  const onBlur = () => {
    if (keyboard.current) leave();
    keyboard.current = false;
  };

  const shown = STORIES[Math.max(0, hover)];
  // Each row's slip lands at its own slight angle, like a ballot dropped on a table.
  const tilt = hover % 2 ? 2 : -3;

  return (
    <section
      id="home-stories"
      data-testid="home-stories"
      aria-labelledby="home-stories-title"
      className="border-t border-border"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 pt-[72px] pb-20 sm:px-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h2
            id="home-stories-title"
            className="font-display text-[56px] leading-none font-extrabold"
          >
            {t('home.storiesTitle')}
          </h2>
          <p className="text-base text-muted-foreground">{t('home.storiesLede')}</p>
        </div>
        <ul onPointerMove={onMove} onPointerLeave={leave} className="border-t-2 border-foreground">
          {STORIES.map((s, i) => {
            const leader = s.mode === 'leader';
            return (
              <li key={s.id} onPointerEnter={onEnter(i)} className="border-b border-border">
                <Link
                  to={`/playground?story=${s.id}`}
                  onFocus={onFocus(i)}
                  onBlur={onBlur}
                  className="group flex flex-wrap items-baseline gap-x-6 gap-y-1 px-2 py-4 text-foreground no-underline"
                >
                  <span className="relative flex-[0_1_300px] text-lg font-bold">
                    <span className="inline-block transition-transform duration-[240ms] ease-[cubic-bezier(.2,.7,.2,1)] group-hover:translate-x-2 group-focus-visible:translate-x-2">
                      {tp(s.titleKey)}
                    </span>
                    <span
                      aria-hidden="true"
                      className="absolute inset-x-0 -bottom-px h-0.5 origin-left scale-x-0 bg-primary transition-transform duration-[480ms] ease-[cubic-bezier(.65,0,.35,1)] group-hover:scale-x-100 group-focus-visible:scale-x-100"
                    />
                  </span>
                  <span className="flex-[999_1_320px] text-base text-muted-foreground">
                    {tp(s.taglineKey)}
                  </span>
                  <span
                    className={`inline-flex flex-none items-center gap-1.5 text-sm font-bold ${leader ? 'text-primary' : 'text-ballot-stamp'}`}
                  >
                    {tp(leader ? 'mode.leader' : 'mode.assembly')}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>

      <div
        ref={slip}
        aria-hidden="true"
        data-testid="home-story-slip"
        className="pointer-events-none fixed top-0 left-0 z-40 hidden w-[232px] pointer-fine:block"
      >
        <div
          className="flex flex-col gap-1.5 border border-border bg-card px-4 pt-3.5 pb-3 transition-[opacity,transform] duration-300 ease-[cubic-bezier(.2,.7,.2,1)] [clip-path:polygon(0_0,84%_0,100%_14%,100%_100%,0_100%)]"
          style={{
            opacity: hover >= 0 ? 1 : 0,
            transform: hover >= 0 ? `rotate(${tilt}deg)` : 'rotate(-8deg) scale(0.86)',
          }}
        >
          <span className="font-display text-[22px] leading-none font-extrabold">
            {tp(shown.titleKey)}
          </span>
          <Sketch figure={figureOf(shown)} />
        </div>
      </div>
    </section>
  );
};

export default StoriesRegister;
