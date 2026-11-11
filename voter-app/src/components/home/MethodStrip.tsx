import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { EASE } from '@/lib/home/motion';
import { ENGINE_RULE, METHOD_WINNERS, winsByCandidate } from '@/lib/home/methods';
import { CANDIDATES, VOTERS, type RuleId } from '@/lib/home/scenario';

// MethodStrip — the hero's thesis at full scale: the same 100 ballots counted by every
// method the app knows, one ballot slip per method, coloured by the candidate it
// elects. The rule picked on the tally sheet lifts its slip (aria-current). Pointing
// at a slip, tapping it or reaching it from the keyboard names its method; the row is
// one tab stop, and the arrow keys move along it.

const WINS = winsByCandidate();
const N = METHOD_WINNERS.length;
const STEP: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 };

const MethodStrip: React.FC<{ active: RuleId; play: boolean }> = ({ active, play }) => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  // On a desktop the strip sits under the map's flight, so it clears away with the rest
  // of the hero; on a phone it scrolls off on its own, after being read (HandoverMap).
  const wide = useMediaQuery('(min-width: 1024px)');
  const activeIndex = METHOD_WINNERS.findIndex((m) => m.rule === ENGINE_RULE[active]);
  const [hover, setHover] = useState<number | null>(null);
  const [cursor, setCursor] = useState(0);
  const slips = useRef<(HTMLButtonElement | null)[]>([]);
  const shown = METHOD_WINNERS[hover ?? activeIndex];
  const label = (i: number) =>
    t('home.methodsElects', {
      rule: tp(`rules.${METHOD_WINNERS[i].rule}`),
      name: CANDIDATES[METHOD_WINNERS[i].winner].name,
    });

  const onKeyDown = (e: React.KeyboardEvent) => {
    const d = STEP[e.key];
    if (!d) return;
    e.preventDefault();
    const next = (cursor + d + N) % N;
    setCursor(next);
    slips.current[next]!.focus();
  };

  return (
    <div
      data-testid="home-methods"
      data-handover-out={wide || undefined}
      className="flex flex-col gap-4 border-t border-border pt-6 [@media(max-height:960px)]:gap-3 [@media(max-height:960px)]:pt-4"
      style={wide ? { opacity: 'calc(1 - var(--handover, 0) * 1.6)' } : undefined}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
        <h2 className="font-display text-[32px] leading-none font-extrabold">
          {t('home.methodsTitle', { n: VOTERS.length, m: N })}
        </h2>
        <ul className="flex flex-wrap gap-x-5 gap-y-1 text-[15px]">
          {CANDIDATES.map((c, i) => (
            <li key={c.name} className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
              <span className="font-bold">{c.name}</span>
              <span className="font-mono text-muted-foreground">{WINS[i]}</span>
            </li>
          ))}
        </ul>
      </div>
      <ol
        aria-label={t('home.methodsNote')}
        onPointerLeave={(e) => e.pointerType === 'mouse' && setHover(null)}
        // 28 slips need ~780 px: they wrap until the hero is wide enough for one row.
        className="flex flex-wrap items-end gap-x-1.5 gap-y-3 lg:flex-nowrap"
      >
        {METHOD_WINNERS.map((m, i) => {
          const c = CANDIDATES[m.winner];
          const on = i === activeIndex;
          return (
            <li
              key={m.rule}
              data-method={m.rule}
              aria-current={on || undefined}
              className={cn(
                // Wrapped (narrow screens), every slip keeps one size; on one row they share it.
                'home-up w-[26px] flex-none transition-transform duration-[240ms] lg:w-auto lg:max-w-[44px] lg:min-w-[22px] lg:flex-1',
                on ? '-translate-y-2' : 'hover:-translate-y-1'
              )}
              style={{
                animationDelay: `${600 + i * 25}ms`,
                animationPlayState: play ? 'running' : 'paused',
              }}
            >
              <button
                type="button"
                ref={(el) => {
                  slips.current[i] = el;
                }}
                tabIndex={i === cursor ? 0 : -1}
                onKeyDown={onKeyDown}
                aria-label={label(i)}
                onPointerEnter={(e) => e.pointerType === 'mouse' && setHover(i)}
                onFocus={() => {
                  setCursor(i);
                  setHover(i);
                }}
                onBlur={() => setHover(null)}
                onClick={() => setHover(i)}
                className="block w-full rounded-sm"
              >
                <svg viewBox="0 0 20 26" aria-hidden="true" className="block h-auto w-full">
                  <path
                    d="M1 1h12l6 6v18H1z"
                    fill={c.color}
                    fillOpacity={on ? 1 : 0.8}
                    className={on ? 'stroke-foreground' : 'stroke-card'}
                    strokeWidth={on ? 1.6 : 1}
                    strokeLinejoin="round"
                    style={{ transition: `fill-opacity 240ms ${EASE.settle}` }}
                  />
                  <path d="M13 1v6h6" fill="none" className="stroke-card" strokeWidth={1} />
                </svg>
              </button>
            </li>
          );
        })}
      </ol>
      <p aria-hidden="true" className="min-h-[1.5em] text-[15px] text-muted-foreground">
        {label(METHOD_WINNERS.indexOf(shown))}
        {hover === null && <span> {t('home.methodsNote')}</span>}
      </p>
    </div>
  );
};

export default MethodStrip;
