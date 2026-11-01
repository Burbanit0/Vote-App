import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { EASE, approach } from '@/lib/home/motion';
import { HERO_DRAW } from '@/lib/home/handover';
import { ENGINE_RULE } from '@/lib/home/methods';
import {
  CANDIDATES,
  RULES,
  RUNOFF_CHOICE,
  TALLY,
  VOTERS,
  countsByName,
  type RuleId,
} from '@/lib/home/scenario';

// HeroInstrument — the homepage's thesis, made live: one electorate on a map and its
// tally sheet. Switching the counting rule re-colours the voters in a wave from the
// new winner, redraws the tally marks, rolls the counts and stamps the winner. The
// electorate and its tallies live in lib/home/scenario.ts, shared with the count
// further down the page, so both always agree.

const NOTE_KEY: Record<RuleId, string> = {
  plurality: 'home.notePlurality',
  runoff: 'home.noteRunoff',
  approval: 'home.noteApproval',
};
const N = VOTERS.length;
const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
const GREY = 'var(--muted-foreground)';
/** Map units the dot and candidate layers drift with the pointer (≈ 2 and 4 px). */
const PARALLAX = [0.35, 0.75];

function dotColor(rule: RuleId, i: number): string {
  if (rule === 'runoff') return CANDIDATES[RUNOFF_CHOICE[i]].color;
  if (rule === 'approval')
    return VOTERS[i].approves.includes(TALLY.approval.winner)
      ? CANDIDATES[TALLY.approval.winner].color
      : GREY;
  return CANDIDATES[VOTERS[i].first].color;
}

const TallyMarks: React.FC<{ n: number; color: string }> = ({ n, color }) => {
  const stroke = {
    stroke: color,
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeDasharray: '1 1',
  };
  return (
    <>
      {Array.from({ length: Math.floor(n / 5) }, (_, g) => (
        <svg key={`g${g}`} width="20" height="16" viewBox="0 0 20 16" aria-hidden="true">
          {['M3 2v12', 'M7 2v12', 'M11 2v12', 'M15 2v12', 'M1 12L18 4'].map((d) => (
            <path key={d} d={d} pathLength={1} style={stroke} />
          ))}
        </svg>
      ))}
      {Array.from({ length: n % 5 }, (_, r) => (
        <svg key={`r${r}`} width="4" height="16" viewBox="0 0 4 16" aria-hidden="true">
          <path d="M2 2v12" pathLength={1} style={stroke} />
        </svg>
      ))}
    </>
  );
};

/** A two-column counter whose digits roll to the new value. */
const Odometer: React.FC<{ value: number; row: number }> = ({ value, row }) => (
  <span aria-hidden="true" className="flex leading-[1.2]">
    {[Math.floor(value / 10) % 10, value % 10].map((d, col) => (
      <span key={col} className="block h-[1.2em] overflow-hidden">
        <span
          className="flex flex-col"
          style={{
            transform: `translateY(${-d * 1.2}em)`,
            transition: `transform 480ms ${EASE.settle} ${col * 60 + row * 40}ms`,
          }}
        >
          {DIGITS.map((n) => (
            <span key={n} className="block h-[1.2em]">
              {n}
            </span>
          ))}
        </span>
      </span>
    ))}
  </span>
);

/** Controlled: the page holds the rule, so the method strip below can echo it. */
const HeroInstrument: React.FC<{ rule: RuleId; onRule: (rule: RuleId) => void }> = ({
  rule,
  onRule,
}) => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const reduce = useReducedMotion();
  // Bumped by each rule change, so the redraw runs on a change and never on mount.
  const [changes, setChanges] = useState(0);
  const tally = TALLY[rule];
  const win = CANDIDATES[tally.winner];
  const ri = RULES.indexOf(rule);

  const sheet = useRef<HTMLDivElement>(null);
  const tray = useRef<HTMLDivElement>(null);
  const layers = useRef<(SVGGElement | null)[]>([]);
  const pointer = useRef({ tx: 0, ty: 0, x: 0, y: 0 });

  const dots = useMemo(() => {
    const w = CANDIDATES[tally.winner];
    return VOTERS.map((v, i) => ({
      x: v.x * HERO_DRAW.w,
      y: v.y * HERO_DRAW.h,
      fill: dotColor(rule, i),
      delay: `${Math.round((Math.hypot(v.x - w.x, v.y - w.y) / 0.8) * 420)}ms`,
    }));
  }, [rule, tally.winner]);

  useEffect(() => {
    if (changes === 0 || reduce) return;
    sheet.current!.querySelectorAll('[data-tally]').forEach((row) =>
      row.querySelectorAll('path').forEach((p, i) =>
        p.animate?.([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], {
          duration: 140,
          delay: 80 + i * 7,
          easing: EASE.settle,
          fill: 'backwards',
        })
      )
    );
    // The stamp lands: the tray takes the knock.
    tray.current!.animate?.(
      [{ transform: 'none' }, { transform: 'translateY(2px)' }, { transform: 'none' }],
      { duration: 200, delay: 230, easing: 'ease-out' }
    );
  }, [changes, reduce]);

  const kick = useFrameLoop(() => {
    const p = pointer.current;
    p.x = approach(p.x, p.tx, 0.08, 0.002);
    p.y = approach(p.y, p.ty, 0.08, 0.002);
    layers.current.forEach((g, i) =>
      g!.setAttribute(
        'transform',
        `translate(${(p.x * PARALLAX[i]).toFixed(3)} ${(p.y * PARALLAX[i]).toFixed(3)})`
      )
    );
    return p.x !== p.tx || p.y !== p.ty;
  });

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType !== 'mouse' || reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    pointer.current.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    pointer.current.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
    kick();
  };
  const onPointerLeave = () => {
    pointer.current.tx = 0;
    pointer.current.ty = 0;
    kick();
  };

  const pick = (r: RuleId) => {
    if (r === rule) return;
    setChanges((c) => c + 1);
    onRule(r);
  };

  return (
    <div
      ref={tray}
      data-testid="hero-instrument"
      className="flex w-full max-w-[560px] min-w-0 flex-col gap-3.5 rounded-2xl bg-envelope p-4 [@media(max-height:960px)]:max-w-[500px]"
      // The tray clears away as the page hands its map over to the count (HandoverMap).
      data-handover-out
      style={{ opacity: 'calc(1 - var(--handover, 0) * 1.6)' }}
    >
      <div data-testid="hero-map" onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>
        <svg
          viewBox={`0 0 ${HERO_DRAW.w} ${HERO_DRAW.h}`}
          role="img"
          aria-label={t('home.mapLabel', {
            n: N,
            rule: tp(`rules.${ENGINE_RULE[rule]}`),
            winner: win.name,
          })}
          className="block h-auto w-full border border-border bg-card"
          // The map itself leaves at once: from here the flying copy carries it.
          data-handover-from
          style={{
            borderRadius: HERO_DRAW.radius,
            opacity: 'clamp(0, calc(1 - var(--handover, 0) * 10000), 1)',
          }}
        >
          <g className="stroke-border" strokeWidth={0.4}>
            <line x1={0} y1={HERO_DRAW.h / 2} x2={HERO_DRAW.w} y2={HERO_DRAW.h / 2} />
            <line x1={HERO_DRAW.w / 2} y1={0} x2={HERO_DRAW.w / 2} y2={HERO_DRAW.h} />
          </g>
          <g
            ref={(el) => {
              layers.current[0] = el;
            }}
          >
            {dots.map((d, i) => (
              <circle
                key={i}
                data-voter
                cx={d.x}
                cy={d.y}
                r={HERO_DRAW.voterR}
                opacity={0.6}
                style={{ fill: d.fill, transition: `fill 480ms ${EASE.settle} ${d.delay}` }}
              />
            ))}
          </g>
          <g
            ref={(el) => {
              layers.current[1] = el;
            }}
          >
            {CANDIDATES.map((c) => (
              <g key={c.name}>
                <circle
                  cx={c.x * HERO_DRAW.w}
                  cy={c.y * HERO_DRAW.h}
                  r={HERO_DRAW.candR}
                  fill={c.color}
                  className="stroke-card"
                  strokeWidth={0.8}
                />
                <text
                  x={c.x * HERO_DRAW.w}
                  y={c.y * HERO_DRAW.h - HERO_DRAW.labelDy}
                  textAnchor="middle"
                  fontSize={HERO_DRAW.label}
                  fontWeight={700}
                  className="fill-foreground"
                >
                  {c.name}
                </text>
              </g>
            ))}
          </g>
        </svg>
      </div>

      <div
        role="radiogroup"
        aria-label={t('home.rulePick')}
        className="relative flex gap-1 rounded-[10px] bg-foreground/10 p-1"
      >
        <span
          aria-hidden="true"
          className="absolute inset-y-1 left-1 w-[calc((100%-16px)/3)] rounded-[7px] bg-primary"
          style={{
            transform: `translateX(calc(${ri * 100}% + ${ri * 4}px))`,
            transition: `transform 300ms ${EASE.settle}`,
          }}
        />
        {RULES.map((r) => (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={rule === r}
            data-testid={`hero-rule-${r}`}
            onClick={() => pick(r)}
            className={cn(
              'relative min-h-11 flex-1 rounded-[7px] px-2 text-[15px] font-bold transition-colors',
              rule === r ? 'text-primary-foreground' : 'text-foreground'
            )}
          >
            {tp(`rules.${ENGINE_RULE[r]}`)}
          </button>
        ))}
      </div>

      <div ref={sheet} className="flex flex-col gap-2 rounded-[10px] bg-card px-4 pt-3.5 pb-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="font-sans text-base font-bold tracking-normal">{t('home.sheet')}</h2>
          <span className="text-sm text-muted-foreground">{t('home.voters', { n: N })}</span>
        </div>
        {CANDIDATES.map((c, i) => {
          const out = tally.out === i;
          return (
            <div
              key={c.name}
              className="relative grid min-h-[34px] grid-cols-[64px_minmax(0,1fr)_40px] items-center gap-3 border-t border-border"
            >
              <span className="flex items-center gap-2 text-[15px] font-bold">
                <span className="h-[9px] w-[9px] rounded-full" style={{ background: c.color }} />
                {c.name}
              </span>
              <div data-tally className="flex flex-wrap items-center gap-x-[5px] gap-y-0.5">
                <TallyMarks n={tally.counts[i]} color={c.color} />
                {out && (
                  <span className="home-up text-sm text-muted-foreground">{t('home.out')}</span>
                )}
              </div>
              <span
                className={cn(
                  'flex justify-end font-mono text-[15px] font-semibold transition-opacity',
                  out && 'opacity-0'
                )}
              >
                <span className="sr-only">{tally.counts[i]}</span>
                <Odometer value={tally.counts[i]} row={i} />
              </span>
              {tally.winner === i && (
                <>
                  <span
                    aria-hidden="true"
                    className="home-bleed absolute top-[3px] right-[52px] h-7 w-[92px] rounded border-[2.5px] border-ballot-stamp"
                  />
                  <span
                    aria-hidden="true"
                    className="home-stamp absolute top-[3px] right-[52px] rounded border-[2.5px] border-ballot-stamp bg-card/80 px-2.5 pt-px pb-0.5 font-display text-[19px] leading-[1.2] font-extrabold tracking-[0.08em] text-ballot-stamp uppercase"
                  >
                    {t('home.elected')}
                  </span>
                </>
              )}
            </div>
          );
        })}
        <p className="mt-0.5 text-[15px] text-muted-foreground">
          {t(NOTE_KEY[rule], { n: N, ...countsByName(rule) })}
        </p>
        <p data-testid="hero-winner" aria-live="polite" className="sr-only">
          {t('home.electedName', { name: win.name })}
        </p>
      </div>
    </div>
  );
};

export default HeroInstrument;
