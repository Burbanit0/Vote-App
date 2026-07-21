import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowRight, ListOrdered, Star, CheckSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import { ruleWinnerFromRanks, type Rule } from '../lib/playgroundVoting';
import {
  GROUPS,
  RANKS,
  FOOD_COUNT,
  approvalScores,
  approvalCountsForK,
} from '../lib/discoverVoteAnim';
import DiscoverVoteAnimation from '../components/home/DiscoverVoteAnimation';

// DecouvrirPage — the on-ramp for someone who only knows the method their country
// uses. Four beats: Anchor (you already know one way to vote) → Rupture (same
// ballots, a different winner, counted before your eyes) → Map (three families,
// plain words) → Play (go do it on a real electorate). The rupture demo runs the
// SAME client engine the Playground uses (ruleWinnerFromRanks over fixed ballots)
// and its animation frames are computed from the same ballots, so the "aha" is
// computed, never illustrated — if a rule changes, the demo changes with it.

// The 12-friends / one-restaurant profile lives in lib/discoverVoteAnim (shared
// with the animation). Here we only need the food faces (emoji + name); indices
// line up with that profile: Pizza=0, Sushi=1, Thaï=2.
const FOODS = [
  { emoji: '🍕', name: 'Pizza' },
  { emoji: '🍣', name: 'Sushi' },
  { emoji: '🍜', name: 'Thaï' },
] as const;

// The four rules the demo flips between, in teaching order (familiar → surprising).
const DEMO_RULES: Rule[] = ['plurality', 'two_round', 'approval', 'condorcet'];
const WHY_KEY: Record<string, string> = {
  plurality: 'discover.why.plurality',
  two_round: 'discover.why.two_round',
  condorcet: 'discover.why.condorcet',
};
// Approval cutoffs offered by the interactive threshold: approve your favourite
// (= plurality), your two favourites (the compromise wins), or everyone (a tie).
const APPROVAL_STOPS: { k: number; labelKey: string }[] = [
  { k: 1, labelKey: 'discover.approve.k1' },
  { k: 2, labelKey: 'discover.approve.k2' },
  { k: 3, labelKey: 'discover.approve.k3' },
];

const FAMILIES = [
  { id: 'rank', Icon: ListOrdered },
  { id: 'score', Icon: Star },
  { id: 'approve', Icon: CheckSquare },
] as const;

const DecouvrirPage: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const [rule, setRule] = React.useState<Rule>('plurality');
  // Approval only: how many options each friend approves (the cutoff that decides).
  const [approvalK, setApprovalK] = React.useState(2);
  const activeIsApproval = rule === 'approval';

  useMetaTags({ title: `Vote Lab — ${t('discover.title')}`, description: t('discover.lede') });

  // Under approval, everyone approving everyone is a dead tie — surface it as such
  // rather than letting the argmax tie-break crown an arbitrary "winner".
  const approvalTie = React.useMemo(
    () => activeIsApproval && new Set(approvalCountsForK(approvalK)).size === 1,
    [activeIsApproval, approvalK]
  );

  const winner = React.useMemo(
    () =>
      ruleWinnerFromRanks(
        RANKS,
        FOOD_COUNT,
        rule,
        rule === 'approval' ? approvalScores(approvalK) : undefined
      ),
    [rule, approvalK]
  );
  const win = FOODS[winner] ?? FOODS[0];

  return (
    <div data-style="tailwind" className="min-h-[calc(100dvh-49px)]">
      {/* ── 1 · Anchor: the method you already know ── */}
      <section className="border-b border-border">
        <div className="container mx-auto max-w-4xl px-4 py-8 sm:py-10">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('discover.eyebrow')}
          </p>
          <h1 className="mt-2 font-display text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
            {t('discover.title')}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
            {t('discover.lede')}
          </p>

          <div className="mt-6 rounded-xl border border-border bg-card p-4 sm:p-5">
            <p className="font-mono text-[0.68rem] uppercase tracking-[0.18em] text-primary">
              {t('discover.s1Kicker')}
            </p>
            <h2 className="mt-1 font-display text-lg font-semibold">{t('discover.s1Title')}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {t('discover.s1Body')}
            </p>
          </div>
        </div>
      </section>

      {/* ── 2 · Rupture: same ballots, a different winner ── */}
      <section className="border-b border-border bg-accent/20">
        <div className="container mx-auto max-w-4xl px-4 py-8 sm:py-10">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('discover.demoKicker')}
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight">
            {t('discover.demoTitle')}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {t('discover.demoIntro')}
          </p>

          {/* The ballots — the SAME twelve, shown once. */}
          <ul className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {GROUPS.map((g, gi) => (
              <li
                key={gi}
                className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3"
              >
                <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted-foreground">
                  {t('discover.friends', { n: g.n })}
                </span>
                <div className="flex items-center gap-1.5 text-lg">
                  {g.rank.map((ci, pos) => {
                    // In approval mode, the top-k options are the ones this group
                    // ticks — shown with a ✓ so the tally is visible, not asserted.
                    const ticked = pos < approvalK;
                    return (
                      <React.Fragment key={ci}>
                        {pos > 0 && <span className="text-xs text-muted-foreground">›</span>}
                        <span
                          title={FOODS[ci].name}
                          className={cn('relative', activeIsApproval && !ticked && 'opacity-25')}
                        >
                          {FOODS[ci].emoji}
                          {activeIsApproval && ticked && (
                            <span className="absolute -right-1.5 -top-1 text-[0.6rem] font-bold text-primary">
                              ✓
                            </span>
                          )}
                        </span>
                      </React.Fragment>
                    );
                  })}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 min-h-[1.25rem] text-xs text-muted-foreground">
            {activeIsApproval ? t('discover.approveHint') : ' '}
          </p>

          {/* The rule selector — flipping it flips the winner, live. */}
          <div
            className="mt-4 flex flex-wrap gap-2"
            role="tablist"
            aria-label={t('discover.demoKicker')}
          >
            {DEMO_RULES.map((id) => {
              const active = id === rule;
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setRule(id)}
                  className={
                    'rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors ' +
                    (active
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-card text-foreground hover:border-primary/40 hover:bg-accent/40')
                  }
                >
                  {tp(`rules.${id}`)}
                </button>
              );
            })}
          </div>

          {/* The count, played out — then the winner + why. aria-live so the
              flip is announced to a screen reader, not only seen. */}
          <div
            aria-live="polite"
            className="mt-4 rounded-xl border border-primary/40 bg-card p-4 sm:p-5"
          >
            <p className="font-mono text-[0.66rem] uppercase tracking-[0.16em] text-muted-foreground">
              {t('discover.winnerLabel')} · {tp(`rules.${rule}`)}
            </p>
            <p className="mt-1 flex items-center gap-3">
              <span className="text-4xl leading-none">{approvalTie ? '🤝' : win.emoji}</span>
              <span
                data-testid="discover-winner"
                className="font-display text-3xl font-bold text-primary"
              >
                {approvalTie ? t('discover.approve.tie') : win.name}
              </span>
            </p>

            {/* Approval's defining knob: how many each friend approves. Sliding it
                slides the winner (favourite-only = plurality = Pizza). */}
            {activeIsApproval && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground">
                  {t('discover.approve.threshold')}
                </span>
                <div
                  className="flex flex-wrap gap-1.5"
                  role="group"
                  aria-label={t('discover.approve.threshold')}
                >
                  {APPROVAL_STOPS.map(({ k, labelKey }) => {
                    const active = k === approvalK;
                    return (
                      <button
                        key={k}
                        type="button"
                        aria-pressed={active}
                        onClick={() => setApprovalK(k)}
                        className={cn(
                          'rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors',
                          active
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
                        )}
                      >
                        {t(labelKey)}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Key on the rule so switching methods restarts the animation; the
                approval threshold re-tallies in place (no remount). */}
            <DiscoverVoteAnimation key={rule} rule={rule} foods={FOODS} approvalK={approvalK} />

            {!activeIsApproval && (
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {t(WHY_KEY[rule])}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── 3 · Map: three families, in plain words ── */}
      <section className="border-b border-border">
        <div className="container mx-auto max-w-4xl px-4 py-8 sm:py-10">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('discover.famKicker')}
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight">
            {t('discover.famTitle')}
          </h2>
          <ul className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {FAMILIES.map(({ id, Icon }) => (
              <li
                key={id}
                className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
              >
                <Icon aria-hidden className="h-5 w-5 text-primary" />
                <h3 className="font-display text-lg font-semibold">
                  {t(`discover.fam.${id}.title`)}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {t(`discover.fam.${id}.desc`)}
                </p>
                <p className="mt-auto pt-1 font-mono text-[0.68rem] uppercase tracking-[0.1em] text-muted-foreground">
                  {t(`discover.fam.${id}.ex`)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── 4 · Play: go see it on a real electorate ── */}
      <section className="bg-accent/20">
        <div className="container mx-auto max-w-4xl px-4 py-8 sm:py-10">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('discover.playKicker')}
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight">
            {t('discover.playTitle')}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {t('discover.playBody')}
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button size="lg" variant="primary" asChild className="px-5">
              <Link to="/playground?story=spoiler">
                {t('discover.playStory')} <ArrowRight aria-hidden className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/playground">{t('discover.playInstrument')}</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default DecouvrirPage;
