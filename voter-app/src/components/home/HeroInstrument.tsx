import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { Instrument } from '@/components/ui/instrument';

// HeroInstrument — the homepage's thesis, made live. A fixed electorate and three
// candidates; switching the counting rule flips the WINNER on the same ballots
// (the spoiler → runoff → consensus story). Self-contained (a ~deterministic
// gaussian electorate + three tiny tallies) so the landing page stays light and
// never depends on the backend. It IS the doorway: the full version is /playground.

type V = { x: number; y: number };
interface Cand {
  name: string;
  x: number;
  y: number;
  color: string;
}

const CANDIDATES: Cand[] = [
  { name: 'Alice', x: -0.6, y: 0.12, color: '#2563eb' },
  { name: 'Carol', x: -0.18, y: -0.16, color: '#16a34a' },
  { name: 'Bob', x: 0.55, y: 0.0, color: '#dc2626' },
];

// Deterministic electorate: three clusters (left bloc split by a centre-left
// spoiler, right bloc) — the configuration that makes the rule decide.
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const clamp1 = (v: number) => Math.max(-0.98, Math.min(0.98, v));

function buildVoters(): V[] {
  const r = mulberry32(7);
  const gauss = () => {
    const u = 1 - r();
    const v = r();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  const clusters = [
    { n: 58, mx: -0.6, my: 0.12, s: 0.13 },
    { n: 30, mx: -0.18, my: -0.16, s: 0.12 },
    { n: 72, mx: 0.55, my: 0.0, s: 0.16 },
  ];
  const out: V[] = [];
  for (const c of clusters)
    for (let i = 0; i < c.n; i++)
      out.push({ x: clamp1(c.mx + gauss() * c.s), y: clamp1(c.my + gauss() * c.s) });
  return out;
}
const VOTERS = buildVoters();

const dist2 = (a: V, b: { x: number; y: number }) => (a.x - b.x) ** 2 + (a.y - b.y) ** 2;
const firstChoice = (v: V): number => {
  let bi = 0;
  let bd = Infinity;
  CANDIDATES.forEach((c, i) => {
    const d = dist2(v, c);
    if (d < bd) {
      bd = d;
      bi = i;
    }
  });
  return bi;
};
const FIRST = VOTERS.map(firstChoice);

type RuleId = 'plurality' | 'runoff' | 'approval';

// Each rule returns its per-candidate score (share of voters, 0..1) + the winner.
function tally(rule: RuleId): { scores: number[]; winner: number } {
  const n = VOTERS.length;
  if (rule === 'plurality') {
    const c = [0, 0, 0];
    FIRST.forEach((i) => (c[i] += 1));
    return { scores: c.map((x) => x / n), winner: c.indexOf(Math.max(...c)) };
  }
  if (rule === 'runoff') {
    const fc = [0, 0, 0];
    FIRST.forEach((i) => (fc[i] += 1));
    const [a, b] = [0, 1, 2].sort((p, q) => fc[q] - fc[p]);
    let av = 0;
    let bv = 0;
    VOTERS.forEach((v) => (dist2(v, CANDIDATES[a]) < dist2(v, CANDIDATES[b]) ? av++ : bv++));
    const scores = [0, 0, 0];
    scores[a] = av / n;
    scores[b] = bv / n;
    return { scores, winner: av >= bv ? a : b };
  }
  // approval: approve every candidate within reach of your position. The radius
  // lets the centrist (Carol) be acceptable across the spectrum — approval's
  // signature pull toward broad consensus.
  const R2 = 0.75 ** 2;
  const c = [0, 0, 0];
  VOTERS.forEach((v) => CANDIDATES.forEach((cd, i) => dist2(v, cd) <= R2 && (c[i] += 1)));
  return { scores: c.map((x) => x / n), winner: c.indexOf(Math.max(...c)) };
}

const RULES: RuleId[] = ['plurality', 'runoff', 'approval'];
const RULE_KEY: Record<RuleId, string> = {
  plurality: 'rules.plurality',
  runoff: 'rules.two_round',
  approval: 'rules.approval',
};
const CAP_KEY: Record<RuleId, string> = {
  plurality: 'home.heroCapPlurality',
  runoff: 'home.heroCapRunoff',
  approval: 'home.heroCapApproval',
};

const toX = (x: number) => ((x + 1) / 2) * 100;
const toY = (y: number) => ((1 - y) / 2) * 100;

const HeroInstrument: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const [rule, setRule] = React.useState<RuleId>('plurality');

  const { scores, winner } = React.useMemo(() => tally(rule), [rule]);
  const pluralityWinner = React.useMemo(() => tally('plurality').winner, []);
  const flipped = winner !== pluralityWinner;
  const win = CANDIDATES[winner];

  return (
    <Instrument
      label={t('home.heroInstrLabel')}
      readout={<span className="text-[0.62rem]">158 · 3 · {VOTERS.length > 0 ? '2D' : ''}</span>}
      className="w-full"
    >
      <div className="flex flex-col gap-2">
        {/* The screen: ideology map */}
        <svg
          viewBox="0 0 100 100"
          className="w-full max-h-[27vh] rounded bg-background"
          role="img"
          aria-label={`${t('home.heroInstrLabel')} — ${win.name}`}
        >
          {/* faint grid */}
          {[20, 40, 60, 80].map((p) => (
            <g key={p} stroke="currentColor" className="text-border" strokeWidth={0.2}>
              <line x1={p} y1={0} x2={p} y2={100} />
              <line x1={0} y1={p} x2={100} y2={p} />
            </g>
          ))}
          {/* axes */}
          <line
            x1={50}
            y1={0}
            x2={50}
            y2={100}
            stroke="currentColor"
            className="text-border"
            strokeWidth={0.5}
          />
          <line
            x1={0}
            y1={50}
            x2={100}
            y2={50}
            stroke="currentColor"
            className="text-border"
            strokeWidth={0.5}
          />

          {/* voters coloured by their first choice (the spatial blocs) */}
          {VOTERS.map((v, i) => (
            <circle
              key={i}
              cx={toX(v.x)}
              cy={toY(v.y)}
              r={0.85}
              fill={CANDIDATES[FIRST[i]].color}
              opacity={0.5}
            />
          ))}

          {/* candidates; the winner under the active rule gets a ring */}
          {CANDIDATES.map((c, i) => {
            const cx = toX(c.x);
            const cy = toY(c.y);
            return (
              <g key={c.name}>
                {i === winner && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={6}
                    fill="none"
                    stroke={c.color}
                    strokeWidth={1}
                    strokeDasharray="2 1.5"
                    style={{ transition: 'cx 300ms, cy 300ms' }}
                  />
                )}
                <circle cx={cx} cy={cy} r={3.2} fill={c.color} stroke="#fff" strokeWidth={1} />
                <text
                  x={cx}
                  y={cy - 5}
                  textAnchor="middle"
                  fontSize={4.4}
                  fontWeight={700}
                  fill="currentColor"
                >
                  {c.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Rule selector */}
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground">
            {t('home.rulePick')}
          </span>
          <div
            role="radiogroup"
            aria-label={t('home.rulePick')}
            className="grid grid-cols-3 gap-1 rounded-lg border border-border bg-muted/40 p-0.5"
          >
            {RULES.map((r) => (
              <button
                key={r}
                type="button"
                role="radio"
                aria-checked={rule === r}
                data-testid={`hero-rule-${r}`}
                onClick={() => setRule(r)}
                className={cn(
                  'flex min-h-8 items-center justify-center truncate rounded-md px-2 text-xs font-medium transition-colors',
                  rule === r
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {tp(RULE_KEY[r])}
              </button>
            ))}
          </div>
        </div>

        {/* Winner readout + per-candidate tally */}
        <div className="rounded-lg border border-border bg-card p-2">
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
              {t('home.heroWinner')}
            </span>
            {flipped && (
              <span className="rounded bg-[var(--color-stamp)]/15 px-1.5 py-0.5 font-mono text-[0.6rem] font-semibold uppercase tracking-wide text-[#9a4513]">
                {t('home.heroFlip')}
              </span>
            )}
          </div>
          <div key={win.name} aria-live="polite" className="hero-pop flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full" style={{ background: win.color }} />
            <span
              data-testid="hero-winner"
              className="font-display text-xl font-bold leading-none"
              style={{ color: win.color }}
            >
              {win.name}
            </span>
          </div>

          <div className="mt-1.5 flex flex-col gap-0.5">
            {CANDIDATES.map((c, i) => (
              <div key={c.name} className="flex items-center gap-2 text-[0.7rem]">
                <span className="w-10 shrink-0 text-muted-foreground">{c.name}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted/60">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.round(scores[i] * 100)}%`,
                      background: c.color,
                      opacity: i === winner ? 1 : 0.45,
                      transition: 'width 300ms ease',
                    }}
                  />
                </div>
                <span className="w-7 text-right font-mono tabular-nums text-muted-foreground">
                  {Math.round(scores[i] * 100)}
                </span>
              </div>
            ))}
          </div>

          <p className="mt-1 text-[0.72rem] leading-snug text-muted-foreground">
            {t(CAP_KEY[rule])}
          </p>
        </div>
      </div>
    </Instrument>
  );
};

export default HeroInstrument;
