import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { candidateColor } from '../../lib/palette';
import regimes, { type BlankVoteStatus } from '../../data/blankVoteRegimes';
import { allBlankVerdicts, type BlankLens, type BlankOutcome } from '../../lib/blankVote';
import { usePlaygroundCtx } from '../playground/PlaygroundController';
import { applyBlankVote, computeRanks } from '../../lib/playgroundVoting';

// BlankVotePanel — a reflection space, not an answer key. Two acts:
//   1) you CAN vote blank (three silences: abstention ≠ blanc ≠ nul);
//   2) the blank wins — now what? Build a result, then watch four real regimes
//      each decide a different fate for the SAME ballots. We describe what
//      exists; we don't prescribe. The closing prompt asks, it doesn't answer.

const CAND_LETTERS = ['A', 'B', 'C'];

type Weights = { cands: number[]; blank: number };

const PRESETS: Record<string, Weights> = {
  balanced: { cands: [38, 32, 10], blank: 20 },
  blankLeads: { cands: [30, 15, 10], blank: 45 },
  blankMajority: { cands: [22, 13, 10], blank: 55 },
};

const LENS_FLAG: Record<BlankLens, string> = {
  france_today: '🇫🇷',
  in_exprimes: '⚖️',
  competitive: '🇺🇾',
  threshold: '🇨🇴',
};

const STATUS_ORDER: BlankVoteStatus[] = [
  'competitive',
  'threshold',
  'counted_separate',
  'symbolic',
  'merged_invalid',
];

const BlankVotePanel: React.FC = () => {
  const { t } = useTranslation('playground');
  const [w, setW] = React.useState<Weights>(PRESETS.balanced);
  const [useReal, setUseReal] = React.useState(false);
  const { leaderCandidates, votingVoters, blank: liveBlank } = usePlaygroundCtx();

  // Real electorate: first-preference shares of the candidates actually
  // configured in the Playground, plus whoever's too far from all of them to
  // pick one (same alienation-radius mechanism as the Stratégie moment's own
  // blank-vote toggle, applied here regardless of whether that toggle is on —
  // this fiche's whole premise is that the blank exists).
  const real = React.useMemo(() => {
    if (leaderCandidates.length < 2 || !votingVoters.length) return null;
    const { expressed, blankCount } = applyBlankVote(
      votingVoters,
      leaderCandidates,
      true,
      liveBlank.intensity
    );
    const counts = new Array(leaderCandidates.length).fill(0);
    for (const r of computeRanks(expressed, leaderCandidates)) counts[r[0]]++;
    const total = votingVoters.length || 1;
    return {
      shares: counts.map((c) => c / total),
      blank: blankCount / total,
      names: leaderCandidates.map((c) => c.name),
    };
  }, [leaderCandidates, votingVoters, liveBlank.intensity]);

  const manualTotal = w.cands.reduce((a, b) => a + b, 0) + w.blank || 1;
  const shares = useReal && real ? real.shares : w.cands.map((c) => c / manualTotal);
  const blank = useReal && real ? real.blank : w.blank / manualTotal;
  const names = useReal && real ? real.names : CAND_LETTERS;
  const verdicts = allBlankVerdicts(shares, blank);

  const setCand = (i: number, v: number) =>
    setW((prev) => ({ ...prev, cands: prev.cands.map((c, j) => (j === i ? v : c)) }));

  const pct = (x: number) => `${Math.round(x * 100)}%`;

  return (
    <div data-testid="blank-vote-panel" className="flex flex-col gap-6">
      {/* ── Act 1 — you CAN vote blank ─────────────────────────────────── */}
      <section className="flex flex-col gap-3">
        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
            {t('blankVote.act1Kicker')}
          </p>
          <h2 className="font-display text-lg font-bold tracking-tight">
            {t('blankVote.act1Title')}
          </h2>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
            {t('blankVote.act1Lede')}
          </p>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-3">
          {(['abstention', 'blanc', 'nul'] as const).map((k) => (
            <div
              key={k}
              data-testid={`silence-${k}`}
              className="rounded-lg border border-border bg-card p-3"
            >
              <p className="text-sm font-semibold">{t(`blankVote.silences.${k}.term`)}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {t(`blankVote.silences.${k}.desc`)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Act 2 — the blank wins, now what? ──────────────────────────── */}
      <section className="flex flex-col gap-3">
        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
            {t('blankVote.act2Kicker')}
          </p>
          <h2 className="font-display text-lg font-bold tracking-tight">
            {t('blankVote.act2Title')}
          </h2>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
            {t('blankVote.act2Lede')}
          </p>
        </div>

        {/* Mixer */}
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('blankVote.mixerTitle')}
            </p>
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                data-testid="blank-real-toggle"
                aria-pressed={useReal}
                onClick={() => setUseReal((v) => !v)}
                className={cn(
                  'rounded-md border px-2 py-0.5 text-[0.7rem]',
                  useReal
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                )}
              >
                {t('blankVote.realToggle')}
              </button>
              {!useReal &&
                Object.keys(PRESETS).map((p) => (
                  <button
                    key={p}
                    type="button"
                    data-testid={`blank-preset-${p}`}
                    onClick={() => setW(PRESETS[p])}
                    className="rounded-md border border-border px-2 py-0.5 text-[0.7rem] text-muted-foreground hover:border-primary/40 hover:text-foreground"
                  >
                    {t(`blankVote.presets.${p}`)}
                  </button>
                ))}
            </div>
          </div>

          {useReal && (
            <p className="mt-2 text-[0.7rem] text-muted-foreground">{t('blankVote.realHint')}</p>
          )}

          <div className="mt-3 flex flex-col gap-2" data-testid="blank-mixer-rows">
            {useReal
              ? names.map((name, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="flex w-28 shrink-0 items-center gap-1.5 truncate">
                      <span
                        aria-hidden
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ background: candidateColor(i) }}
                      />
                      {name}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full"
                        style={{ width: pct(shares[i]), background: candidateColor(i) }}
                      />
                    </div>
                    <span className="w-10 text-right tabular-nums text-muted-foreground">
                      {pct(shares[i])}
                    </span>
                  </div>
                ))
              : w.cands.map((c, i) => (
                  <label key={i} className="flex items-center gap-2 text-xs">
                    <span className="flex w-16 shrink-0 items-center gap-1.5">
                      <span
                        aria-hidden
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ background: candidateColor(i) }}
                      />
                      {CAND_LETTERS[i]}
                    </span>
                    <input
                      type="range"
                      data-testid={`blank-cand-${i}`}
                      className="flex-1"
                      min={0}
                      max={100}
                      value={c}
                      onChange={(e) => setCand(i, Number(e.target.value))}
                    />
                    <span className="w-10 text-right tabular-nums text-muted-foreground">
                      {pct(shares[i])}
                    </span>
                  </label>
                ))}
            <div className="flex items-center gap-2 text-xs">
              <span className={cn('flex shrink-0 items-center gap-1.5', useReal ? 'w-28' : 'w-16')}>
                <span
                  aria-hidden
                  className="h-2.5 w-2.5 rounded-full border border-dashed border-muted-foreground"
                />
                {t('blankVote.blankLabel')}
              </span>
              {useReal ? (
                <>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-1.5 rounded-full bg-muted-foreground"
                      style={{ width: pct(blank) }}
                    />
                  </div>
                  <span
                    className="w-10 text-right font-semibold tabular-nums"
                    data-testid="blank-real-share"
                  >
                    {pct(blank)}
                  </span>
                </>
              ) : (
                <>
                  <input
                    type="range"
                    data-testid="blank-share"
                    className="flex-1 accent-[color:var(--muted-foreground)]"
                    min={0}
                    max={100}
                    value={w.blank}
                    onChange={(e) => setW((prev) => ({ ...prev, blank: Number(e.target.value) }))}
                  />
                  <span className="w-10 text-right font-semibold tabular-nums">{pct(blank)}</span>
                </>
              )}
            </div>
          </div>

          {/* Composition bar */}
          <div
            data-testid="blank-composition"
            className="mt-3 flex h-3 w-full overflow-hidden rounded-full"
          >
            {shares.map((s, i) => (
              <span key={i} style={{ width: pct(s), background: candidateColor(i) }} />
            ))}
            <span
              style={{
                width: pct(blank),
                background:
                  'repeating-linear-gradient(45deg, var(--border) 0 4px, transparent 4px 8px)',
              }}
            />
          </div>
        </div>

        {/* Four fates for the same ballots */}
        <div className="grid gap-2.5 sm:grid-cols-2">
          {verdicts.map((v) => {
            const winnerName = v.winner === null ? null : names[v.winner];
            return (
              <div
                key={v.lens}
                data-testid={`lens-card-${v.lens}`}
                className={cn(
                  'flex flex-col gap-1 rounded-lg border p-3',
                  v.redo ? 'border-primary/50 bg-primary/5' : 'border-border bg-card'
                )}
              >
                <p className="text-sm font-semibold">
                  <span aria-hidden className="mr-1">
                    {LENS_FLAG[v.lens]}
                  </span>
                  {t(`blankVote.lens.${v.lens}.label`)}
                </p>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {t(`blankVote.lens.${v.lens}.mechanism`)}
                </p>
                <p className="mt-1 flex items-center gap-2 text-xs">
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[0.68rem] font-semibold',
                      v.redo ? 'bg-primary/15 text-primary' : 'bg-muted text-foreground'
                    )}
                  >
                    {v.redo ? t('blankVote.redoBadge') : t('blankVote.electedBadge')}
                  </span>
                  <span className="text-muted-foreground">
                    {outcomeLine(t, v.outcome, winnerName, v.winnerShareOfExprimes, pct)}
                  </span>
                </p>
              </div>
            );
          })}
        </div>

        {/* Open reflection — questions, not answers */}
        <div className="rounded-lg border border-dashed border-primary/40 bg-primary/5 p-3">
          <p className="text-sm font-semibold text-primary">{t('blankVote.reflectTitle')}</p>
          <ul className="mt-1.5 flex list-disc flex-col gap-1 pl-5 text-xs leading-relaxed text-muted-foreground">
            <li>{t('blankVote.reflectQ1')}</li>
            <li>{t('blankVote.reflectQ2')}</li>
            <li>{t('blankVote.reflectQ3')}</li>
          </ul>
        </div>
      </section>

      {/* ── What already exists — 16 real regimes ──────────────────────── */}
      <section className="flex flex-col gap-3">
        <div>
          <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
            {t('blankVote.worldKicker')}
          </p>
          <h2 className="font-display text-lg font-bold tracking-tight">
            {t('blankVote.worldTitle')}
          </h2>
          <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
            {t('blankVote.worldLede')}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table
            className="w-full min-w-[32rem] border-collapse text-xs"
            data-testid="blank-regimes"
          >
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-1.5 font-medium">{t('blankVote.col.country')}</th>
                <th className="py-1.5 font-medium">{t('blankVote.col.status')}</th>
                <th className="py-1.5 text-right font-medium">{t('blankVote.col.rate')}</th>
                <th className="py-1.5 text-center font-medium">{t('blankVote.col.impact')}</th>
              </tr>
            </thead>
            <tbody>
              {sortByStatusThenRate(regimes).map((r) => (
                <tr key={r.country} className="border-b border-border/60">
                  <td className="py-1.5">
                    <span aria-hidden className="mr-1.5">
                      {r.flag}
                    </span>
                    {r.country}
                  </td>
                  <td className="py-1.5">
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-[0.66rem] font-medium',
                        r.impact_on_result
                          ? 'bg-primary/15 text-primary'
                          : 'bg-muted text-muted-foreground'
                      )}
                      title={r.description}
                    >
                      {t(`blankVote.status.${r.legal_status}`)}
                    </span>
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {r.blank_rate_typical.toLocaleString(undefined, { minimumFractionDigits: 1 })}%
                  </td>
                  <td className="py-1.5 text-center">
                    {r.impact_on_result ? (
                      <span className="text-primary" title={t('blankVote.impactYes')}>
                        ●
                      </span>
                    ) : (
                      <span className="text-border" title={t('blankVote.impactNo')}>
                        ○
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[0.68rem] text-muted-foreground/80">{t('blankVote.source')}</p>
      </section>
    </div>
  );
};

// Compose the dynamic verdict line without embedding markup in i18n params.
function outcomeLine(
  t: (k: string, o?: Record<string, unknown>) => string,
  outcome: BlankOutcome,
  winner: string | null,
  share: number,
  pct: (x: number) => string
): string {
  switch (outcome) {
    case 'elected':
      return t('blankVote.outcome.elected', { winner, pct: pct(share) });
    case 'no_majority':
      return t('blankVote.outcome.no_majority', { winner, pct: pct(share) });
    case 'blank_wins':
      return t('blankVote.outcome.blank_wins', { pct: pct(share) });
    case 'annulled':
      return t('blankVote.outcome.annulled', { pct: pct(share) });
  }
}

function sortByStatusThenRate(data: typeof regimes) {
  return [...data].sort((a, b) => {
    const d = STATUS_ORDER.indexOf(a.legal_status) - STATUS_ORDER.indexOf(b.legal_status);
    return d !== 0 ? d : b.blank_rate_typical - a.blank_rate_typical;
  });
}

export default BlankVotePanel;
