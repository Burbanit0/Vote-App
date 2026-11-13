import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Fish, Pizza, Soup } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Segmented } from '@/components/ui/segmented';
import { RevealSection, RiseWords, Slip } from '@/components/ui/slip';
import { useMetaTags } from '../hooks/useMetaTags';
import { useReveal } from '../hooks/useReveal';
import CuriosityQuestions from '../components/shared/common/CuriosityQuestions';
import { ruleWinnerFromRanks, type Rule } from '../lib/playgroundVoting';
import {
  GROUPS,
  RANKS,
  FOOD_COUNT,
  approvalScores,
  approvalCountsForK,
} from '../lib/discoverVoteAnim';
import DiscoverVoteAnimation, {
  FoodIcon,
  type Food,
} from '../components/home/DiscoverVoteAnimation';
import { textTone } from '../lib/palette';
import { CANDIDATES } from '../lib/home/scenario';

// DecouvrirPage — the on-ramp for someone who only knows the method their country
// uses. Four beats: Anchor (you already know one way to vote) → Rupture (same
// ballots, a different winner, counted before your eyes) → Map (three families,
// plain words) → Play (go do it on a real electorate). The rupture demo runs the
// SAME client engine the Playground uses (ruleWinnerFromRanks over fixed ballots)
// and its animation frames are computed from the same ballots, so the "aha" is
// computed, never illustrated — if a rule changes, the demo changes with it.
//
// Dressed like the homepage ("Bureau de vote"): the twelve friends' ballots are
// ballot slips, the count is a hand tally, the result is stamped in violet. The
// three restaurants take the homepage's three colours for the same three roles:
// Pizza wins plurality (red, like Bob), Sushi the runoff (blue, like Alice), Thaï
// is the compromise (green, like Carol). Each is drawn in its text tone (lib/palette), so
// its strokes and its name keep their contrast on a dark card too.

// The 12-friends / one-restaurant profile lives in lib/discoverVoteAnim (shared
// with the animation); indices line up with it: Pizza=0, Sushi=1, Thaï=2.
const [ALICE, CAROL, BOB] = CANDIDATES.map((c) => textTone(c.color));
const FOODS: readonly Food[] = [
  { Icon: Pizza, name: 'Pizza', color: BOB },
  { Icon: Fish, name: 'Sushi', color: ALICE },
  { Icon: Soup, name: 'Thaï', color: CAROL },
];

// The four rules the demo flips between, in teaching order (familiar → surprising).
const DEMO_RULES: Rule[] = ['plurality', 'two_round', 'approval', 'condorcet'];
const WHY_KEY: Record<string, string> = {
  plurality: 'discover.why.plurality',
  two_round: 'discover.why.two_round',
  condorcet: 'discover.why.condorcet',
};
// Approval cutoffs offered by the interactive threshold: approve your favourite
// (= plurality), your two favourites (the compromise wins), or everyone (a tie).
const APPROVAL_STOPS = [
  { k: '1', labelKey: 'discover.approve.k1' },
  { k: '2', labelKey: 'discover.approve.k2' },
  { k: '3', labelKey: 'discover.approve.k3' },
] as const;

/** A tilt per ballot, so the three don't land alike. */
const TILT = ['-5deg', '4deg', '-3deg'];

/** CSS delay for an entrance `ms` after its section shows. */
const after = (ms: number): React.CSSProperties => ({ animationDelay: `${ms}ms` });

/**
 * What each family's ballot looks like: a slip, ranked, scored or ticked. On reveal its
 * outline is drawn, then its fold, then its three lines are filled in, from `delay` ms.
 */
const FamilySlip: React.FC<{ id: 'rank' | 'score' | 'approve'; delay: number }> = ({
  id,
  delay,
}) => (
  <svg viewBox="0 0 120 150" aria-hidden="true" className="h-auto w-24">
    <path
      d="M4 4h82l30 30v112H4z"
      pathLength={1}
      className="stroke-draw fill-card stroke-foreground"
      style={{ ...after(delay), animationDuration: '0.9s' }}
      strokeWidth={2}
      strokeLinejoin="round"
    />
    <path
      d="M86 4v30h30"
      pathLength={1}
      fill="none"
      className="stroke-draw stroke-foreground"
      style={after(delay + 700)}
      strokeWidth={2}
    />
    {FOODS.map((f, i) => {
      const y = 58 + i * 30;
      return (
        <g key={f.name} className="home-up" style={after(delay + 800 + i * 90)}>
          <rect x={44} y={y - 4} width={56} height={8} rx={4} className="fill-muted" />
          {id === 'rank' && (
            <text
              x={24}
              y={y + 6}
              textAnchor="middle"
              fontSize={18}
              fontWeight={800}
              style={{ fill: f.color }}
              className="font-display"
            >
              {[2, 3, 1][i]}
            </text>
          )}
          {id === 'score' &&
            [0, 1, 2].map((k) => (
              <circle
                key={k}
                cx={14 + k * 10}
                cy={y}
                r={3.5}
                style={{ fill: k < [1, 2, 3][i] ? f.color : 'none', stroke: f.color }}
                strokeWidth={1.5}
              />
            ))}
          {id === 'approve' && (
            <>
              <rect
                x={14}
                y={y - 9}
                width={18}
                height={18}
                rx={3}
                fill="none"
                style={{ stroke: f.color }}
                strokeWidth={2}
              />
              {i > 0 && (
                <path
                  d={`M18 ${y}l4 4 7-8`}
                  fill="none"
                  style={{ stroke: f.color }}
                  strokeWidth={2.4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
            </>
          )}
        </g>
      );
    })}
  </svg>
);

const FAMILIES = ['rank', 'score', 'approve'] as const;

const DecouvrirPage: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const [rule, setRule] = React.useState<Rule>('plurality');
  // Approval only: how many options each friend approves (the cutoff that decides).
  const [approvalStop, setApprovalStop] = React.useState<(typeof APPROVAL_STOPS)[number]['k']>('2');
  const approvalK = Number(approvalStop);
  const activeIsApproval = rule === 'approval';

  const ballots = useReveal<HTMLUListElement>();
  const families = useReveal<HTMLUListElement>();

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
        rule === 'approval' ? approvalScores(approvalK) : undefined,
        FOODS.map((f) => f.name)
      ),
    [rule, approvalK]
  );
  const win = FOODS[winner] ?? FOODS[0];

  return (
    <div data-style="tailwind">
      {/* ── 1 · Anchor: the method you already know ── */}
      <section className="mx-auto flex max-w-6xl flex-wrap items-end gap-x-16 gap-y-10 px-4 pt-14 pb-16 sm:px-6">
        <div className="flex min-w-0 flex-[1_1_520px] flex-col gap-5">
          <p className="home-up text-[15px] font-bold text-primary">{t('discover.eyebrow')}</p>
          {/* Each word rises out of its own mask, like the homepage's headline lines. */}
          <h1 className="font-display text-[clamp(44px,5.4vw,80px)] leading-[0.92] font-extrabold">
            <RiseWords text={t('discover.title')} delay={80} />
          </h1>
          <p
            className="home-up max-w-[36rem] text-xl text-muted-foreground"
            style={{ animationDelay: '200ms' }}
          >
            {t('discover.lede')}
          </p>
        </div>
        {/* The starting point, on a ballot slip that unfolds from its corner: the one rule
            you already know. */}
        <Slip
          fold={28}
          className="slip-unfold min-w-0 flex-[1_1_320px] p-6"
          style={{ animationDelay: '420ms' }}
        >
          <p className="text-[15px] font-bold text-primary">{t('discover.s1Kicker')}</p>
          <h2 className="mt-1 font-display text-[28px] leading-none font-extrabold">
            {t('discover.s1Title')}
          </h2>
          <p className="mt-3 text-base text-muted-foreground">{t('discover.s1Body')}</p>
        </Slip>
      </section>

      {/* ── 2 · Rupture: same ballots, a different winner ── */}
      <section className="border-y border-border bg-muted">
        <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-16 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-3">
            <h2 className="font-display text-[44px] leading-none font-extrabold sm:text-[56px]">
              {t('discover.demoTitle')}
            </h2>
            <p className="max-w-xl text-base text-muted-foreground">{t('discover.demoIntro')}</p>
          </div>

          {/* The ballots — the SAME twelve, shown once, one slip per group of friends. */}
          <ul data-reveal ref={ballots} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {GROUPS.map((g, gi) => (
              <li
                key={gi}
                data-testid={`discover-ballot-${gi}`}
                style={{ ...after(gi * 120), '--tilt': TILT[gi] } as React.CSSProperties}
                className="ballot-drop"
              >
                <Slip className="flex h-full flex-col gap-3 px-5 pt-4 pb-5">
                  <span className="font-display text-[22px] leading-none font-extrabold">
                    {t('discover.friends', { n: g.n })}
                  </span>
                  <ol className="flex flex-col gap-1.5">
                    {g.rank.map((ci, pos) => {
                      // In approval mode, the top-k options are the ones this group
                      // ticks: shown with a tick so the tally is visible, not asserted.
                      const ticked = pos < approvalK;
                      const food = FOODS[ci];
                      return (
                        <li
                          key={ci}
                          className={cn(
                            'flex items-center gap-2.5 text-[15px] transition-opacity duration-300 motion-reduce:transition-none',
                            activeIsApproval && !ticked && 'opacity-35'
                          )}
                        >
                          <span className="w-4 font-mono text-sm font-semibold text-muted-foreground">
                            {pos + 1}
                          </span>
                          <FoodIcon food={food} />
                          <span className="font-semibold">{food.name}</span>
                          {activeIsApproval && ticked && (
                            // The tick is drawn, as a pen would.
                            <svg
                              data-testid="discover-tick"
                              viewBox="0 0 14 14"
                              aria-hidden="true"
                              className="ml-auto h-3.5 w-3.5"
                            >
                              <path
                                d="M2 7.5l3 3 7-8"
                                pathLength={1}
                                fill="none"
                                className="stroke-draw"
                                style={{ stroke: food.color, ...after(pos * 90) }}
                                strokeWidth={2.2}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                </Slip>
              </li>
            ))}
          </ul>

          {/* The count: pick a rule, read the winner off the tally. */}
          <div className="flex flex-col gap-5 rounded-2xl bg-envelope p-4 sm:p-5">
            <Segmented
              label={t('discover.demoKicker')}
              value={rule}
              onChange={setRule}
              options={DEMO_RULES.map((id) => ({
                value: id,
                label: tp(`rules.${id}`),
                testid: `discover-rule-${id}`,
              }))}
            />
            {/* aria-live so the flip is announced to a screen reader, not only seen. */}
            <div aria-live="polite" className="rounded-xl bg-card p-5 sm:p-6">
              <p className="text-sm font-semibold text-muted-foreground">
                {t('discover.winnerLabel')}: {tp(`rules.${rule}`)}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-4">
                {!approvalTie && (
                  <win.Icon
                    aria-hidden
                    className="h-10 w-10"
                    strokeWidth={1.5}
                    style={{ color: win.color }}
                  />
                )}
                {/* The new winner rises out of its mask each time it changes. */}
                <span className="-mb-[0.08em] overflow-hidden pb-[0.08em]">
                  <span
                    key={`${rule}-${approvalK}`}
                    data-testid="discover-winner"
                    className="home-rise block font-display text-[48px] leading-none font-extrabold"
                    style={{ color: approvalTie ? undefined : win.color }}
                  >
                    {approvalTie ? t('discover.approve.tie') : win.name}
                  </span>
                </span>
                {/* The result, stamped: the one violet on the page. Keyed so it lands again
                    each time the winner changes. */}
                {!approvalTie && (
                  <span key={`${rule}-${approvalK}`} className="relative">
                    <span
                      aria-hidden="true"
                      className="home-bleed absolute inset-0 rounded border-[2.5px] border-ballot-stamp"
                    />
                    <span className="home-stamp block rounded border-[2.5px] border-ballot-stamp px-2.5 pt-px pb-0.5 font-display text-[19px] leading-[1.2] font-extrabold tracking-[0.08em] text-ballot-stamp uppercase">
                      {t('discover.stamp')}
                    </span>
                  </span>
                )}
              </div>

              {/* Approval's defining knob: how many each friend approves. Sliding it
                  slides the winner (favourite-only = plurality = Pizza). */}
              {activeIsApproval && (
                <div className="mt-5 flex flex-col gap-2">
                  <span className="text-sm font-semibold text-muted-foreground">
                    {t('discover.approve.threshold')}
                  </span>
                  <Segmented
                    label={t('discover.approve.threshold')}
                    value={approvalStop}
                    onChange={setApprovalStop}
                    options={APPROVAL_STOPS.map(({ k, labelKey }) => ({
                      value: k,
                      label: t(labelKey),
                      testid: `discover-approve-${k}`,
                    }))}
                  />
                  <p className="text-sm text-muted-foreground">{t('discover.approveHint')}</p>
                </div>
              )}

              {/* Key on the rule so switching methods restarts the animation; the
                  approval threshold re-tallies in place (no remount). */}
              <DiscoverVoteAnimation key={rule} rule={rule} foods={FOODS} approvalK={approvalK} />

              {!activeIsApproval && (
                <p className="mt-4 border-t border-border pt-4 text-[15px] text-muted-foreground">
                  {t(WHY_KEY[rule])}
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── 3 · Map: three families, each drawn as the ballot it asks for ── */}
      <section className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-16 sm:px-6">
        <h2 className="font-display text-[44px] leading-none font-extrabold sm:text-[56px]">
          {t('discover.famTitle')}
        </h2>
        <ul
          data-reveal
          ref={families}
          className="grid grid-cols-1 gap-x-10 gap-y-10 sm:grid-cols-3"
        >
          {FAMILIES.map((id, fi) => (
            <li
              key={id}
              className="home-up flex flex-col gap-3 border-t-2 border-primary pt-5"
              style={after(fi * 160)}
            >
              <FamilySlip id={id} delay={fi * 160 + 120} />
              <h3 className="font-display text-[32px] leading-none font-extrabold">
                {t(`discover.fam.${id}.title`)}
              </h3>
              <p className="text-base text-muted-foreground">{t(`discover.fam.${id}.desc`)}</p>
              <p className="mt-auto text-sm font-semibold text-foreground">
                {t(`discover.fam.${id}.ex`)}
              </p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── 3.5 · Follow your curiosity: questions → the story that answers ── */}
      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <CuriosityQuestions />
      </section>

      {/* ── 4 · Play: go see it on a real electorate ── */}
      <RevealSection className="border-t border-border bg-muted">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-20 sm:px-6">
          <h2 className="-mb-[0.08em] max-w-3xl overflow-hidden pb-[0.08em] font-display text-[52px] leading-[0.92] font-extrabold lg:text-[80px]">
            <span className="home-rise block">{t('discover.playTitle')}</span>
          </h2>
          <p className="max-w-[34rem] text-xl text-muted-foreground">{t('discover.playBody')}</p>
          <div className="flex flex-wrap items-center gap-3">
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
      </RevealSection>
    </div>
  );
};

export default DecouvrirPage;
