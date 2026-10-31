import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pause, Play } from 'lucide-react';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import {
  BALLOTS,
  PILE_X,
  STEPS,
  MAP,
  VIEW,
  approvalArea,
  candidatePoint,
  captionPose,
  countFrame,
  stampPoint,
  voterPoint,
} from '@/lib/home/countFrame';
import { CANDIDATES, VOTERS, countsByName, type RuleId } from '@/lib/home/scenario';
import { approach, clamp01 } from '@/lib/home/motion';
import { COUNT_DRAW } from '@/lib/home/handover';
import { countPin } from './countPin';

// CountStory — the homepage's long scroll: one screen pinned while the next five
// screens of scroll play the count (cast, plurality, runoff, approval, verdict).
// React renders the drawing once; a frame loop writes countFrame(P) into it, with a
// little inertia so a flick of the wheel glides. React only re-renders when the
// chapter or the stamp changes. Under reduced motion the count jumps from chapter
// end to chapter end.

const INERTIA = 0.12;
/** One screen of the count, played back by the Play button. */
const PLAY_MS_PER_SCREEN = 2600;
const TICKS = [
  'tickIntro',
  'tickVotes',
  'tickPlurality',
  'tickRunoff',
  'tickApproval',
  'tickVerdict',
];
const N = VOTERS.length;
const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

/** The copy for a chapter reads the counts of the rule it is about. */
const CHAPTER_RULE: (RuleId | null)[] = [null, null, 'plurality', 'runoff', 'approval', null];
const chapterCounts = (i: number) => {
  const rule = CHAPTER_RULE[i];
  return rule ? { n: N, ...countsByName(rule) } : { n: N };
};

const MUTED = 'var(--muted-foreground)';
/**
 * The caption, the box, the piles and the scrubber come in once the hero's map is most
 * of the way over (HandoverMap): one lead at a time, the map first.
 */
const AFTER_THE_MAP = 'calc((var(--handover, 1) - 0.6) * 2.5)';

/** Writes an attribute only when it changes: most ballots sit still on most frames. */
const setAttr = (el: Element, k: string, v: string) => {
  if (el.getAttribute(k) !== v) el.setAttribute(k, v);
};

const setStyle = (el: HTMLElement | SVGElement, k: 'opacity' | 'transform' | 'fill', v: string) => {
  if (el.style[k] !== v) el.style[k] = v;
};

/** The count's "Elected" stamp, above the pile of whoever the rule just elected. */
const SvgStamp: React.FC<{ rule: RuleId; label: string }> = ({ rule, label }) => {
  const at = stampPoint(rule);
  return (
    <g transform={`translate(${at.x} ${at.y})`}>
      <g className="home-svg-stamp">
        <rect
          x="-62"
          y="-20"
          width="124"
          height="40"
          rx="5"
          className="fill-card stroke-ballot-stamp"
          strokeWidth={3.5}
          opacity="0.92"
        />
        <text
          y="10"
          textAnchor="middle"
          fontSize="28"
          fontWeight={800}
          letterSpacing="3"
          className="fill-ballot-stamp font-display uppercase"
        >
          {label}
        </text>
      </g>
    </g>
  );
};

const CountStory: React.FC = () => {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const [step, setStep] = useState(0);
  const [stamp, setStamp] = useState<RuleId | null>(null);
  const [playing, setPlaying] = useState(false);

  const track = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const ballots = useRef<(SVGRectElement | null)[]>([]);
  const voters = useRef<(SVGCircleElement | null)[]>([]);
  const caps = useRef<(HTMLDivElement | null)[]>([]);
  const castDigits = useRef<(SVGGElement | null)[]>([]);
  const pileDigits = useRef<(SVGGElement | null)[]>([]);
  const pileNums = useRef<(SVGGElement | null)[]>([]);
  const areas = useRef<(SVGEllipseElement | null)[]>([]);
  const box = useRef<SVGGElement>(null);
  const fill = useRef<HTMLDivElement>(null);
  const playButton = useRef<HTMLButtonElement>(null);
  const loop = useRef({ smooth: NaN, lastP: NaN, last: 0, playing: false });

  const geometry = () => countPin(track.current!, stage.current!);

  const draw = (P: number) => {
    const f = countFrame(P);
    f.ballots.forEach((b, i) => {
      const el = ballots.current[i]!;
      setAttr(el, 'x', (-b.w / 2).toFixed(1));
      setAttr(el, 'y', (-b.h / 2).toFixed(1));
      setAttr(el, 'width', b.w.toFixed(1));
      setAttr(el, 'height', b.h.toFixed(1));
      setAttr(
        el,
        'transform',
        `translate(${b.x.toFixed(1)} ${b.y.toFixed(1)}) rotate(${b.rot.toFixed(1)})`
      );
      setAttr(el, 'fill', b.fill);
      setAttr(el, 'opacity', b.o.toFixed(2));
      setAttr(el, 'stroke-width', b.sw.toFixed(2));
    });
    f.lit.forEach((on, i) =>
      setStyle(voters.current[i]!, 'fill', on ? CANDIDATES[VOTERS[i].first].color : MUTED)
    );
    f.areas.forEach((a, i) => {
      setAttr(areas.current[i]!, 'opacity', a.toFixed(3));
      setStyle(areas.current[i]!, 'transform', `scale(${(0.2 + 0.8 * a).toFixed(3)})`);
    });
    setAttr(box.current!, 'transform', `translate(0 ${f.jolt.toFixed(1)})`);
    [Math.floor(f.cast / 100) % 10, Math.floor(f.cast / 10) % 10, f.cast % 10].forEach((d, i) =>
      setStyle(castDigits.current[i]!, 'transform', `translateY(${-d * 20}px)`)
    );
    f.landed.forEach((n, ci) => {
      setStyle(
        pileDigits.current[ci * 2]!,
        'transform',
        `translateY(${-(Math.floor(n / 10) % 10) * 24}px)`
      );
      setStyle(pileDigits.current[ci * 2 + 1]!, 'transform', `translateY(${-(n % 10) * 24}px)`);
      setStyle(pileNums.current[ci]!, 'opacity', P >= 1.15 ? '1' : '0');
    });
    caps.current.forEach((el, i) => {
      const c = captionPose(P, i);
      setStyle(el!, 'opacity', c.o.toFixed(3));
      setStyle(el!, 'transform', `translateY(${c.y.toFixed(1)}px)`);
    });
    setStyle(fill.current!, 'transform', `scaleX(${(P / STEPS).toFixed(4)})`);
    setStep(f.step);
    setStamp(f.stamp);
  };

  const kick = useFrameLoop((now) => {
    const L = loop.current;
    const { H, top } = geometry();
    let more = false;
    if (L.playing) {
      const dt = L.last ? Math.min(64, now - L.last) : 16;
      L.last = now;
      const end = top + STEPS * H;
      const next = Math.max(window.scrollY, top) + (H * dt) / PLAY_MS_PER_SCREEN;
      window.scrollTo(0, Math.min(next, end));
      if (next >= end) setPlaying(false);
      else more = true;
    }
    const y = window.scrollY;
    L.smooth = reduce || Number.isNaN(L.smooth) ? y : approach(L.smooth, y, INERTIA);
    if (L.smooth !== y) more = true;
    let P = clamp01((L.smooth - top) / (STEPS * H)) * STEPS;
    if (reduce) P = Math.round(P);
    if (P !== L.lastP) {
      L.lastP = P;
      draw(P);
    }
    if (!more) L.last = 0;
    return more;
  });

  useEffect(() => {
    loop.current.playing = playing;
    if (!playing) return;
    kick();
    // Any wheel, touch or key stops the playback, except on the button itself: its
    // own click toggles, and stopping first would have that click restart it.
    const stop = (e: Event) => {
      if (!playButton.current!.contains(e.target as Node)) setPlaying(false);
    };
    const events = ['wheel', 'touchstart', 'keydown'] as const;
    events.forEach((e) => window.addEventListener(e, stop, { passive: true }));
    return () => events.forEach((e) => window.removeEventListener(e, stop));
  }, [playing, kick]);

  useEffect(() => {
    loop.current.lastP = NaN;
    kick();
    window.addEventListener('scroll', kick, { passive: true });
    window.addEventListener('resize', kick);
    return () => {
      window.removeEventListener('scroll', kick);
      window.removeEventListener('resize', kick);
    };
  }, [kick, reduce]);

  const goTo = (i: number) => {
    setPlaying(false);
    const { H, top } = geometry();
    window.scrollTo({ top: top + i * H, behavior: reduce ? 'auto' : 'smooth' });
  };
  const togglePlay = () => {
    const { H, top } = geometry();
    // Played to the end: start over.
    if (!playing && window.scrollY >= top + STEPS * H - 2) window.scrollTo(0, top);
    setPlaying(!playing);
  };

  const label = t(`home.stage${step}`, chapterCounts(step));

  return (
    <section
      ref={track}
      id="home-count"
      data-testid="home-count"
      aria-labelledby="home-count-title"
      className="relative h-[calc((100dvh-49px)*6)]"
    >
      <div
        ref={stage}
        className="sticky top-[49px] flex h-[calc(100dvh-49px)] flex-col overflow-hidden"
      >
        <h2 id="home-count-title" className="sr-only">
          {t('home.countTitle')}
        </h2>
        <svg
          viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={label}
          className="min-h-0 w-full flex-1"
          data-handover-to
        >
          {/* The map: shown once the hero's has landed on it (HandoverMap flies it in). */}
          <g style={{ opacity: 'clamp(0, calc((var(--handover, 1) - 0.9999) * 10000), 1)' }}>
            <rect
              x="40"
              y="160"
              width="400"
              height="380"
              rx={COUNT_DRAW.radius}
              className="fill-card stroke-border"
              strokeWidth={1.2}
            />
            <g className="stroke-border" strokeWidth={1}>
              <line x1="40" y1="350" x2="440" y2="350" />
              <line x1="240" y1="160" x2="240" y2="540" />
            </g>
            {/* Approval: each candidate's area, the voters who approve them. Clipped to
                the map: no voter lives outside it. */}
            <clipPath id="home-count-map">
              <rect x={MAP.x} y={MAP.y} width={MAP.w} height={MAP.h} rx={COUNT_DRAW.radius} />
            </clipPath>
            <g clipPath="url(#home-count-map)">
              {CANDIDATES.map((c, i) => {
                const a = approvalArea(i);
                return (
                  <ellipse
                    key={c.name}
                    ref={(el) => {
                      areas.current[i] = el;
                    }}
                    {...a}
                    opacity="0"
                    fill={c.color}
                    fillOpacity={0.1}
                    stroke={c.color}
                    strokeOpacity={0.75}
                    strokeWidth={1.5}
                    strokeDasharray="6 5"
                    style={{ transformOrigin: `${a.cx}px ${a.cy}px`, transform: 'scale(0.2)' }}
                  />
                );
              })}
            </g>
            {VOTERS.map((_, i) => {
              const p = voterPoint(i);
              return (
                <circle
                  key={i}
                  ref={(el) => {
                    voters.current[i] = el;
                  }}
                  cx={p.x}
                  cy={p.y}
                  r={COUNT_DRAW.voterR}
                  opacity="0.75"
                  style={{ fill: MUTED }}
                />
              );
            })}
            {CANDIDATES.map((c, i) => {
              const p = candidatePoint(i);
              return (
                <g key={c.name}>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={COUNT_DRAW.candR}
                    fill={c.color}
                    className="stroke-card"
                    strokeWidth={2.5}
                  />
                  <text
                    x={p.x}
                    y={p.y - COUNT_DRAW.labelDy}
                    textAnchor="middle"
                    fontSize={COUNT_DRAW.label}
                    fontWeight={700}
                    className="fill-foreground"
                  >
                    {c.name}
                  </text>
                </g>
              );
            })}
          </g>

          {/* The box and the piles come in behind the flying map. */}
          <g style={{ opacity: AFTER_THE_MAP }}>
            <g ref={box}>
              <rect
                x="500"
                y="300"
                width="120"
                height="170"
                rx="6"
                className="fill-envelope stroke-primary"
                strokeWidth={1.6}
                opacity="0.6"
              />
              <rect x="536" y="296" width="48" height="8" rx="2" className="fill-foreground" />
              <rect x="528" y="336" width="64" height="24" rx="4" className="fill-foreground" />
              <clipPath id="home-count-counter">
                <rect x="528" y="336" width="64" height="24" rx="4" />
              </clipPath>
              <g clipPath="url(#home-count-counter)">
                {[544, 560, 576].map((x, i) => (
                  <g
                    key={x}
                    ref={(el) => {
                      castDigits.current[i] = el;
                    }}
                    style={{ transition: 'transform 240ms cubic-bezier(.2,.7,.2,1)' }}
                  >
                    {DIGITS.map((n) => (
                      <text
                        key={n}
                        x={x}
                        y={354 + n * 20}
                        textAnchor="middle"
                        fontSize="16"
                        fontWeight={600}
                        className="fill-background font-mono"
                      >
                        {n}
                      </text>
                    ))}
                  </g>
                ))}
              </g>
            </g>

            {CANDIDATES.map((c, ci) => (
              <g key={c.name}>
                <line
                  x1={PILE_X[ci] - 34}
                  y1="552"
                  x2={PILE_X[ci] + 34}
                  y2="552"
                  className="stroke-foreground"
                  strokeWidth={1.5}
                />
                <text
                  x={PILE_X[ci]}
                  y="578"
                  textAnchor="middle"
                  fontSize="16"
                  fontWeight={700}
                  className="fill-foreground"
                >
                  {c.name}
                </text>
                <clipPath id={`home-count-pile-${ci}`}>
                  <rect x={PILE_X[ci] - 14} y="586" width="28" height="26" />
                </clipPath>
                <g
                  ref={(el) => {
                    pileNums.current[ci] = el;
                  }}
                  style={{ opacity: 0, transition: 'opacity 240ms ease' }}
                >
                  <g clipPath={`url(#home-count-pile-${ci})`}>
                    {[PILE_X[ci] - 6, PILE_X[ci] + 6].map((x, col) => (
                      <g
                        key={x}
                        ref={(el) => {
                          pileDigits.current[ci * 2 + col] = el;
                        }}
                        style={{ transition: 'transform 240ms cubic-bezier(.2,.7,.2,1)' }}
                      >
                        {DIGITS.map((n) => (
                          <text
                            key={n}
                            x={x}
                            y={606 + n * 24}
                            textAnchor="middle"
                            fontSize="18"
                            fontWeight={600}
                            fill={c.color}
                            className="font-mono"
                          >
                            {n}
                          </text>
                        ))}
                      </g>
                    ))}
                  </g>
                </g>
              </g>
            ))}
          </g>

          {BALLOTS.map((_, i) => (
            <rect
              key={i}
              ref={(el) => {
                ballots.current[i] = el;
              }}
              x="-6.5"
              y="-4"
              width="13"
              height="8"
              rx="1"
              fill="#FFFFFF"
              stroke="#18212F"
              opacity="0"
            />
          ))}

          {stamp && <SvgStamp key={stamp} rule={stamp} label={t('home.elected')} />}
        </svg>

        {/* The captions share one grid cell, so the block is as tall as the longest one
            and the drawing below never runs under a caption. */}
        <div
          className="pointer-events-none order-first grid px-6 pt-[5vh] sm:pl-[5vw] lg:pr-20"
          style={{ opacity: AFTER_THE_MAP }}
        >
          {Array.from({ length: STEPS + 1 }, (_, i) => (
            <div
              key={i}
              ref={(el) => {
                caps.current[i] = el;
              }}
              className="max-w-[62rem] [grid-area:1/1]"
              style={{ opacity: i === 0 ? 1 : 0 }}
            >
              <h3 className="font-display text-[34px] leading-[0.95] font-extrabold sm:text-5xl xl:text-6xl">
                {t(`home.cap${i}Title`)}
              </h3>
              <p className="mt-2.5 max-w-[34rem] text-base text-muted-foreground sm:text-[19px]">
                {t(`home.cap${i}Text`, chapterCounts(i))}
              </p>
            </div>
          ))}
        </div>

        <div
          className="flex items-center gap-5 px-6 pt-2 pb-10 sm:pl-[5vw] lg:pr-20"
          data-handover-in
          style={{ opacity: AFTER_THE_MAP }}
        >
          <button
            type="button"
            onClick={togglePlay}
            aria-label={t(playing ? 'home.pause' : 'home.play')}
            ref={playButton}
            data-testid="home-count-play"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-[1.5px] border-foreground bg-card text-foreground"
          >
            {playing ? (
              <Pause aria-hidden className="h-4 w-4" />
            ) : (
              <Play aria-hidden className="h-4 w-4" />
            )}
          </button>
          <div className="relative h-11 flex-1">
            <div className="absolute inset-x-0 top-[21px] h-0.5 bg-border" />
            <div
              ref={fill}
              className="absolute inset-x-0 top-[21px] h-0.5 origin-left bg-primary"
              style={{ transform: 'scaleX(0)' }}
            />
            {TICKS.map((key, i) => {
              const on = i === step;
              const past = i <= step;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => goTo(i)}
                  aria-label={t('home.tickLabel', { n: i + 1, name: t(`home.${key}`) })}
                  aria-current={on ? 'step' : undefined}
                  data-testid={`home-count-tick-${i}`}
                  className="absolute top-0 -ml-[22px] flex h-11 w-11 items-center justify-center"
                  style={{ left: `${(i * 100) / STEPS}%` }}
                >
                  <span
                    className={`block h-2.5 w-2.5 rounded-full border-2 transition-transform ${past ? 'border-primary bg-primary' : 'border-muted-foreground bg-card'} ${on ? 'scale-150' : ''}`}
                  />
                  <span
                    aria-hidden="true"
                    className={`absolute top-10 left-1/2 hidden -translate-x-1/2 text-[13px] whitespace-nowrap text-muted-foreground sm:block ${on ? 'font-bold' : ''}`}
                  >
                    {t(`home.${key}`)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CountStory;
