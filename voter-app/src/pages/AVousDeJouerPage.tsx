import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { Modal } from '@/components/ui/modal';
import { useMetaTags } from '../hooks/useMetaTags';
import { candidateColor } from '../lib/palette';
import { track } from '../lib/analytics';
import { useVotingLabels } from '../hooks/useVotingLabels';
import { buildTraceFromBallots } from '../lib/voteTrace';
import DepouillementPanel from '../components/play/DepouillementPanel';
import BallotRegister from '../components/play/BallotRegister';
import Term from '../components/playground/Term';
import {
  BALLOT_LANGUAGES,
  RULES_FOR,
  ballotFrom,
  pipsFrom,
  orderOf,
  type Ballot,
  type BallotLanguage,
  type BallotOptions,
} from '../lib/ballotLanguages';
import {
  CANDIDATES,
  VOTER_COUNT,
  DEFAULT_YOU,
  MAX_BLOC,
  ELECTORATE_FIRST_CHOICE,
  bestResponse,
  pivot,
  winnerWith,
  tallyBallots,
  yourRankOf,
  type Posture,
} from '../lib/votePlay';
import type { Rule } from '../lib/playgroundVoting';

// AVousDeJouerPage — you become one voter in a small, close election. You fill your
// ballot in a booth, and CAST it: the vote is then sealed. You cannot nudge it while
// watching the result — the whole page fights the "my vote is 1/n, let me game it"
// reflex, so the vote must be a commitment. To change anything you re-enter the booth
// and vote again (a fresh commitment, before/after rather than a live toggle).
//
// The ballot LANGUAGE is what decides how much of your opinion reaches the count, and
// therefore which counting methods exist at all. The counting method is the system,
// not your vote, so it stays explorable after casting: "here is how each method would
// count your sealed ballot" — the app's own thesis.

const POINT_BUDGET = 10;

const POSTURES: Posture[] = ['sincere', 'strategic', 'abstain'];

// ── The weight of one voice, at real scale ──────────────────────────────────
// A large electorate, so the "1 over n" belief is at its most intuitive — and at
// its most wrong. Florida 2000 is the anchor: 537 certified votes out of 5 963 110
// ballots cast, which is 0.009 % of the electorate, and 269 people changing their
// mind. The margin is what decides an election, and the margin does not care how
// big the electorate is.
const BIG_N = 6_000_000;
const FLORIDA = { margin: 537, total: 5_963_110 };
// Log slider: 100 votes (razor-thin) → 1 000 000 (a landslide), 25 steps a decade.
const marginAt = (v: number): number => Math.round(100 * Math.pow(10, v / 25));
const sliderAt = (margin: number): number => Math.round(25 * Math.log10(margin / 100));

/** The sealed vote — opinion, ballot language, and how it was filled. Frozen at cast. */
interface Cast {
  you: number[];
  lang: BallotLanguage;
  posture: Posture;
  opt: BallotOptions;
}

// Each glyph is the mark that language actually leaves on paper.
const GLYPH: Record<BallotLanguage, React.ReactNode> = {
  one: <span className="font-mono text-sm font-bold">✗</span>,
  rank: <span className="font-mono text-[0.6rem] font-bold tracking-tight">1·2·3</span>,
  approve: <span className="font-mono text-sm font-bold">✓✓</span>,
  score: <span className="font-mono text-[0.6rem] font-bold tracking-tight">1–5</span>,
  points: <span className="font-mono text-[0.7rem] leading-none">●●●</span>,
};

/** What a language writes for candidate i — used to spot where a tactical ballot strays. */
const markKind = (lang: BallotLanguage, b: Ballot, i: number): number =>
  lang === 'one'
    ? b.rank[0] === i
      ? 1
      : 0
    : lang === 'rank'
      ? b.rank.indexOf(i)
      : (b.score?.[i] ?? 0);

/** Who a tactical ballot pushes forward — the human summary of the lie. */
const tacticNames = (b: Ballot, lang: BallotLanguage): string => {
  if (lang === 'approve' || lang === 'score') {
    const top = CANDIDATES.filter((_, i) => b.score?.[i] === 1).map((c) => c.name);
    return top.length ? top.join(', ') : '—';
  }
  return CANDIDATES[b.rank[0]]?.name ?? '—';
};

/** Registration ticks — the instrument's corner marks, as on the lab bench. */
const Corners: React.FC = () => (
  <>
    {[
      'left-1.5 top-1.5 border-l border-t',
      'right-1.5 top-1.5 border-r border-t',
      'bottom-1.5 left-1.5 border-b border-l',
      'bottom-1.5 right-1.5 border-b border-r',
    ].map((c) => (
      <span
        key={c}
        aria-hidden
        className={cn('pointer-events-none absolute h-2.5 w-2.5 border-primary/50', c)}
      />
    ))}
  </>
);

// A labelled knob inside the ballot — rendered ONLY where the language forces a
// tactical decision, so its very presence is the message: on this paper, "sincere"
// does not determine what you write.
const KnobRow: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="mt-3 flex flex-col gap-1 border-t border-dashed border-border pt-2.5">
    <span className="text-[0.7rem] font-medium text-[var(--color-stamp)]">{label}</span>
    {children}
  </div>
);

/**
 * The paper object with its marks. Used editable in the booth (with the tactical
 * knobs as children) and read-only in the sealed display. Abstention leaves it blank
 * and struck; a tactical ballot tints the rows where it departs from an honest one.
 */
const BallotPaper: React.FC<{
  lang: BallotLanguage;
  ballot: Ballot | null;
  sincere: Ballot;
  strategic: boolean;
  testId: string;
  children?: React.ReactNode;
}> = ({ lang, ballot, sincere, strategic, testId, children }) => {
  const { t } = useTranslation();
  const pips = ballot?.score ? pipsFrom(ballot.score, POINT_BUDGET) : [];
  return (
    <div
      data-testid={testId}
      className={cn(
        'relative mx-auto w-full max-w-[30rem] rotate-[-0.7deg] rounded-sm border bg-card px-5 py-4 shadow-md',
        ballot ? 'border-primary/25' : 'border-dashed border-border opacity-55'
      )}
    >
      <Corners />
      {!ballot && (
        <span
          data-testid={`${testId}-abstain`}
          className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 -rotate-6 text-center font-mono text-sm font-bold uppercase tracking-[0.3em] text-[var(--color-stamp)]"
        >
          {t('play.posture.abstain')}
        </span>
      )}
      <p className="border-b border-dashed border-border pb-2 text-center font-mono text-[0.6rem] uppercase tracking-[0.28em] text-muted-foreground">
        {t('play.ballotPaper')}
      </p>

      <ul className="mt-3 flex flex-col gap-0.5">
        {CANDIDATES.map((c, i) => {
          const grade = ballot ? Math.round((ballot.score?.[i] ?? 0) * 4) + 1 : 0;
          const strayed =
            !!ballot && strategic && markKind(lang, ballot, i) !== markKind(lang, sincere, i);
          return (
            <li
              key={c.name}
              className="flex items-center justify-between gap-3 rounded px-1.5 py-1 text-sm"
              style={
                strayed
                  ? { background: 'color-mix(in srgb, var(--color-stamp) 12%, transparent)' }
                  : undefined
              }
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  aria-hidden
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: candidateColor(i) }}
                />
                <span className="truncate">{c.name}</span>
              </span>

              <span
                data-testid={`${testId}-mark-${i}`}
                className="flex shrink-0 items-center gap-1 font-mono text-[var(--color-stamp)]"
              >
                {!ballot && <span className="text-xs text-muted-foreground">—</span>}

                {ballot &&
                  lang === 'one' &&
                  (ballot.rank[0] === i ? (
                    <span className="text-lg font-bold leading-none">✗</span>
                  ) : (
                    <span className="h-4 w-4 rounded-[3px] border border-border" />
                  ))}

                {ballot && lang === 'rank' && (
                  <span className="text-base font-bold leading-none">
                    {ballot.rank.indexOf(i) + 1}
                  </span>
                )}

                {ballot &&
                  lang === 'approve' &&
                  (ballot.score?.[i] === 1 ? (
                    <span className="text-base font-bold leading-none">✓</span>
                  ) : (
                    <span className="h-4 w-4 rounded-[3px] border border-border" />
                  ))}

                {ballot && lang === 'score' && (
                  <span className="flex items-center gap-0.5">
                    {[1, 2, 3, 4, 5].map((g) => (
                      <span
                        key={g}
                        aria-hidden
                        className={cn(
                          'h-3.5 w-3.5 rounded-[3px] border text-center text-[0.55rem] leading-[0.8rem]',
                          g <= grade
                            ? 'border-[var(--color-stamp)] bg-[var(--color-stamp)]/20 font-bold'
                            : 'border-border'
                        )}
                      >
                        {g <= grade ? g : ''}
                      </span>
                    ))}
                  </span>
                )}

                {ballot && lang === 'points' && (
                  <span className="flex items-center gap-1">
                    <span className="flex gap-0.5">
                      {Array.from({ length: POINT_BUDGET }, (_, p) => (
                        <span
                          key={p}
                          aria-hidden
                          className={cn(
                            'h-2 w-2 rounded-full',
                            p < (pips[i] ?? 0) ? 'bg-[var(--color-stamp)]' : 'border border-border'
                          )}
                        />
                      ))}
                    </span>
                    <span className="w-4 text-right text-xs tabular-nums">{pips[i] ?? 0}</span>
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>

      <div aria-hidden className="mt-3 border-b border-dashed border-border" />
      {children}
    </div>
  );
};

const AVousDeJouerPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { ruleLabels } = useVotingLabels();

  // ── The draft ballot — what you edit inside the booth. ──
  const [draftYou, setDraftYou] = React.useState<number[]>(DEFAULT_YOU);
  const [draftLang, setDraftLang] = React.useState<BallotLanguage>('one');
  const [draftPosture, setDraftPosture] = React.useState<Posture>('sincere');
  const [approveK, setApproveK] = React.useState(2);
  const [contrast, setContrast] = React.useState(1);
  const [concentration, setConcentration] = React.useState(1);
  const [boothOpen, setBoothOpen] = React.useState(false);

  // ── The sealed vote, and the live analysis of it (not part of the vote). ──
  const [cast, setCast] = React.useState<Cast | null>(null);
  const [bloc, setBloc] = React.useState(1);
  const [rule, setRule] = React.useState<Rule>('plurality');
  const [margin, setMargin] = React.useState(FLORIDA.margin);

  useMetaTags({ title: `Vote Lab — ${t('play.title')}`, description: t('play.lede') });

  const draftOpt: BallotOptions = { approveK, contrast, concentration, levels: 5 };

  // Analysis always reads the SEALED vote; before the first cast it falls back to the
  // draft so the hooks run, but nothing downstream is rendered until `cast` exists.
  const eff: Cast = cast ?? {
    you: draftYou,
    lang: draftLang,
    posture: draftPosture,
    opt: draftOpt,
  };
  const { you, lang, posture } = eff;
  const opt = eff.opt;

  const rules = RULES_FOR[lang];
  // Keep the examined method valid for the sealed language.
  React.useEffect(() => {
    if (!RULES_FOR[lang].includes(rule)) setRule(RULES_FOR[lang][0]);
  }, [lang, rule]);
  const activeRule = rules.includes(rule) ? rule : rules[0];

  const myOrder = React.useMemo(() => orderOf(you), [you]);

  const perRule = React.useMemo(() => {
    const sincereBallot = ballotFrom(you, lang, opt);
    return rules.map((r) => {
      const best = bestResponse(you, lang, r, opt, bloc);
      return {
        rule: r,
        sincereBallot,
        sincere: winnerWith(sincereBallot, lang, r, bloc),
        strategic: best.winner,
        strategicBallot: best.ballot,
        abstain: winnerWith(null, lang, r),
        pays: !best.sincereIsBest,
      };
    });
  }, [you, lang, rules, bloc, opt]);

  const row = perRule.find((r) => r.rule === activeRule) ?? perRule[0];
  const paysCount = perRule.filter((r) => r.pays).length;

  const num = React.useMemo(() => new Intl.NumberFormat(i18n.language), [i18n.language]);
  const pct = React.useMemo(() => {
    const coarse = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 });
    const fine = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 4 });
    return (x: number): string => `${(x * 100 < 0.1 ? fine : coarse).format(x * 100)} %`;
  }, [i18n.language]);

  const { toFlip, toTempt } = React.useMemo(
    () => pivot(you, lang, activeRule, opt),
    [you, lang, activeRule, opt]
  );

  // The sealed ballot's marks, under your cast posture. Abstention has no paper.
  const ballot: Ballot | null =
    posture === 'abstain'
      ? null
      : posture === 'strategic'
        ? row.strategicBallot
        : row.sincereBallot;

  const winner =
    (posture === 'abstain' ? row.abstain : posture === 'strategic' ? row.strategic : row.sincere) ??
    -1;
  const myRank = yourRankOf(you, winner);
  const sincereRank = yourRankOf(you, row.sincere);

  // The exact ballots being counted (base electorate + your bloc, in the cast
  // language) — the transparent count replays these, and the register lists them.
  const tally = React.useMemo(() => tallyBallots(ballot, lang, bloc), [ballot, lang, bloc]);
  const trace = React.useMemo(
    () => buildTraceFromBallots(CANDIDATES, tally.ranks, tally.scores, activeRule),
    [tally, activeRule]
  );
  // Your ballots sit last in the tally; none when you abstain.
  const mineFrom = tally.ranks.length - (ballot ? bloc : 0);

  // First-choice camps: the base electorate, plus your camp (you + those like you).
  const myFav = myOrder[0];
  const camps = React.useMemo(
    () => ELECTORATE_FIRST_CHOICE.map((base, i) => base + (i === myFav ? bloc : 0)),
    [myFav, bloc]
  );
  const leader = camps.reduce((best, n, i) => (n > camps[best] ? i : best), 0);
  const totalVoters = VOTER_COUNT + bloc;

  // ── The booth's live preview (draft, not sealed). Strategic previews against the
  // language's first method; downstream it recomputes per examined method. ──
  const draftOrder = React.useMemo(() => orderOf(draftYou), [draftYou]);
  const draftSincere = ballotFrom(draftYou, draftLang, draftOpt);
  const draftBallot: Ballot | null =
    draftPosture === 'abstain'
      ? null
      : draftPosture === 'strategic'
        ? bestResponse(draftYou, draftLang, RULES_FOR[draftLang][0], draftOpt, 1).ballot
        : draftSincere;

  const castVote = () => {
    setCast({
      you: draftYou,
      lang: draftLang,
      posture: draftPosture,
      opt: { approveK, contrast, concentration, levels: 5 },
    });
    setRule(RULES_FOR[draftLang][0]);
    setBloc(1);
    setBoothOpen(false);
    track('play_ballot_cast', { lang: draftLang, posture: draftPosture });
  };

  // Funnel: did they reach & engage the weight section? Fire once, not per drag.
  const weightExplored = React.useRef(false);
  const markWeight = () => {
    if (weightExplored.current) return;
    weightExplored.current = true;
    track('play_weight_explored');
  };

  return (
    <div data-style="tailwind" className="min-h-[calc(100dvh-49px)] bg-background">
      <div className="container mx-auto max-w-5xl px-4 py-8 sm:py-10">
        {/* ── Masthead: the thesis ── */}
        <header>
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {t('play.eyebrow')}
          </p>
          <h1 className="mt-2 max-w-3xl font-display text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
            {t('play.title')}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
            {t('play.lede', { n: VOTER_COUNT })}
          </p>
        </header>

        {!cast ? (
          /* ── Before the vote: the booth invitation. Nothing to analyse yet. ── */
          <section className="mt-8 rounded-xl border border-border bg-card p-6 sm:p-8">
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
              {t('play.vote.kicker')}
            </p>
            <h2 className="mt-1 max-w-2xl font-display text-xl font-bold tracking-tight">
              {t('play.vote.prompt', { n: VOTER_COUNT })}
            </h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {CANDIDATES.map((c, i) => (
                <span
                  key={c.name}
                  className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-sm"
                >
                  <span
                    aria-hidden
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: candidateColor(i) }}
                  />
                  {c.name}
                </span>
              ))}
            </div>
            <button
              type="button"
              data-testid="play-vote-open"
              onClick={() => setBoothOpen(true)}
              className="mt-6 rounded-md border border-primary bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
            >
              {t('play.vote.open')}
            </button>
          </section>
        ) : (
          /* ── After the vote: the sealed ballot. It cannot be edited in place. ── */
          <section
            data-testid="play-sealed-strip"
            className="mt-8 flex flex-col gap-5 rounded-xl border border-primary/30 bg-card p-5 sm:flex-row sm:items-center"
          >
            <div className="sm:w-[28rem] sm:shrink-0">
              <BallotPaper
                lang={lang}
                ballot={ballot}
                sincere={row.sincereBallot}
                strategic={posture === 'strategic'}
                testId="play-sealed"
              />
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                {t('play.sealed.kicker')}
                <span className="-rotate-3 rounded border-2 border-[var(--color-stamp)] px-1.5 py-0.5 text-[0.6rem] font-bold text-[var(--color-stamp)]">
                  {t('play.sealed.stamp')}
                </span>
              </p>
              <p className="mt-2 text-sm">
                {t('play.sealed.summary', {
                  lang: t(`play.lang.${lang}`),
                  posture: t(`play.posture.${posture}`),
                })}
              </p>
              {posture === 'strategic' && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('play.sealed.strategicNote', { method: ruleLabels[activeRule] })}
                </p>
              )}
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                {t('play.sealed.locked')}
              </p>
              <button
                type="button"
                data-testid="play-revote"
                onClick={() => setBoothOpen(true)}
                className="mt-3 rounded-md border border-primary px-3 py-1.5 text-sm font-semibold text-primary transition-colors hover:bg-primary/10"
              >
                {t('play.sealed.revote')}
              </button>
            </div>
          </section>
        )}

        {/* ── The booth: fill the ballot, then cast it. ── */}
        <Modal
          show={boothOpen}
          onHide={() => setBoothOpen(false)}
          size="xl"
          scrollable
          data-testid="play-booth"
        >
          <Modal.Header closeButton>
            <Modal.Title>{t('play.booth.title')}</Modal.Title>
          </Modal.Header>
          <Modal.Body className="flex flex-col gap-5">
            <p className="text-sm text-muted-foreground">{t('play.booth.hint')}</p>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
              {/* Your opinion */}
              <section data-testid="play-opinion" className="h-fit">
                <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('play.opinionKicker')}
                </p>
                <h3 className="mt-0.5 font-display text-lg font-semibold">
                  {t('play.opinionTitle')}
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {t('play.opinionHint')}
                </p>
                <div className="mt-4 flex flex-col gap-3">
                  {CANDIDATES.map((c, i) => (
                    <label key={c.name} className="flex flex-col gap-1">
                      <span className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1.5">
                          <span
                            aria-hidden
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ background: candidateColor(i) }}
                          />
                          {c.name}
                        </span>
                        <span className="font-mono text-xs tabular-nums text-muted-foreground">
                          {Math.round(draftYou[i] * 100)}
                        </span>
                      </span>
                      <input
                        data-testid={`play-affinity-${i}`}
                        type="range"
                        min={0}
                        max={100}
                        value={Math.round(draftYou[i] * 100)}
                        aria-label={c.name}
                        onChange={(e) =>
                          setDraftYou((prev) =>
                            prev.map((v, j) => (j === i ? Number(e.target.value) / 100 : v))
                          )
                        }
                      />
                    </label>
                  ))}
                </div>
                <p className="mt-4 border-t border-border pt-3 font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground">
                  {t('play.yourOrder')}
                </p>
                <p data-testid="play-order" className="mt-1 text-sm font-medium">
                  {draftOrder.map((i) => CANDIDATES[i].name).join(' › ')}
                </p>
              </section>

              {/* The ballot */}
              <section className="flex flex-col gap-4">
                <div>
                  <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                    {t('play.ballotKicker')}
                  </p>
                  <div
                    role="radiogroup"
                    aria-label={t('play.ballotKicker')}
                    className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-5"
                  >
                    {BALLOT_LANGUAGES.map((id) => {
                      const on = id === draftLang;
                      return (
                        <button
                          key={id}
                          type="button"
                          role="radio"
                          aria-checked={on}
                          data-testid={`play-lang-${id}`}
                          onClick={() => setDraftLang(id)}
                          className={cn(
                            'flex flex-col items-center gap-1 rounded-lg border px-2 py-2 transition-colors',
                            on
                              ? 'border-primary bg-primary text-primary-foreground shadow-sm'
                              : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
                          )}
                        >
                          <span className={on ? 'text-primary-foreground' : 'text-primary'}>
                            {GLYPH[id]}
                          </span>
                          <span className="text-center text-[0.68rem] font-medium leading-tight">
                            {t(`play.lang.${id}`)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                    {t(`play.says.${draftLang}`)}
                  </p>
                </div>

                <BallotPaper
                  lang={draftLang}
                  ballot={draftBallot}
                  sincere={draftSincere}
                  strategic={draftPosture === 'strategic'}
                  testId="play-ballot"
                >
                  {/* The tactical knob — only where "sincere" is under-determined. */}
                  {draftPosture !== 'abstain' && draftLang === 'approve' && (
                    <KnobRow label={t('play.knob.approve', { k: approveK })}>
                      <input
                        data-testid="play-knob"
                        type="range"
                        min={1}
                        max={CANDIDATES.length}
                        value={approveK}
                        onChange={(e) => setApproveK(Number(e.target.value))}
                      />
                    </KnobRow>
                  )}
                  {draftPosture !== 'abstain' && draftLang === 'score' && (
                    <KnobRow label={t('play.knob.score')}>
                      <input
                        data-testid="play-knob"
                        type="range"
                        min={100}
                        max={400}
                        value={contrast * 100}
                        onChange={(e) => setContrast(Number(e.target.value) / 100)}
                      />
                    </KnobRow>
                  )}
                  {draftPosture !== 'abstain' && draftLang === 'points' && (
                    <KnobRow label={t('play.knob.points')}>
                      <input
                        data-testid="play-knob"
                        type="range"
                        min={100}
                        max={500}
                        value={concentration * 100}
                        onChange={(e) => setConcentration(Number(e.target.value) / 100)}
                      />
                    </KnobRow>
                  )}
                </BallotPaper>

                {/* How you fill it in */}
                <div>
                  <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                    {t('play.posture.kicker')}
                  </p>
                  <div
                    role="radiogroup"
                    aria-label={t('play.posture.kicker')}
                    className="mt-2 flex flex-wrap gap-1.5"
                  >
                    {POSTURES.map((p) => {
                      const on = p === draftPosture;
                      return (
                        <button
                          key={p}
                          type="button"
                          role="radio"
                          aria-checked={on}
                          data-testid={`play-posture-${p}`}
                          onClick={() => setDraftPosture(p)}
                          className={cn(
                            'rounded-md border px-3 py-1.5 text-sm transition-colors',
                            on
                              ? 'border-primary bg-primary text-primary-foreground'
                              : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                          )}
                        >
                          {t(`play.posture.${p}`)}
                        </button>
                      );
                    })}
                  </div>
                  {draftPosture === 'strategic' && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {t('play.booth.strategicNote')}
                    </p>
                  )}
                </div>
              </section>
            </div>
          </Modal.Body>
          <Modal.Footer>
            <button
              type="button"
              onClick={() => setBoothOpen(false)}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {t('play.booth.cancel')}
            </button>
            <button
              type="button"
              data-testid="play-cast"
              onClick={castVote}
              className="rounded-md border border-primary bg-primary px-5 py-1.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
            >
              {t('play.booth.cast')}
            </button>
          </Modal.Footer>
        </Modal>

        {/* ── Everything below is the analysis of the SEALED vote. ── */}
        {cast && (
          <>
            {/* ── Your weight: how many like you it takes ── */}
            <section className="mt-7 rounded-xl border border-border bg-card p-4 sm:p-5">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                {t('play.poidsKicker')}
              </p>
              <label className="mt-2 flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">
                  {t('play.bloc.label', { n: bloc, total: VOTER_COUNT + bloc })}
                </span>
                <input
                  data-testid="play-bloc"
                  type="range"
                  min={1}
                  max={MAX_BLOC}
                  value={bloc}
                  aria-label={t('play.bloc.label', { n: bloc, total: VOTER_COUNT + bloc })}
                  onChange={(e) => setBloc(Number(e.target.value))}
                />
              </label>

              <p
                data-testid="play-verdict"
                className="mt-3 border-t border-border pt-3 text-sm leading-relaxed"
              >
                {posture === 'abstain'
                  ? t(
                      row.abstain === row.sincere
                        ? 'play.verdict.abstainSame'
                        : 'play.verdict.abstainDiffer',
                      { winner: CANDIDATES[row.abstain]?.name ?? '—', n: bloc }
                    )
                  : posture === 'strategic'
                    ? row.pays
                      ? t('play.verdict.pays', {
                          how: t(`play.tactic.${lang}`, {
                            names: tacticNames(row.strategicBallot, lang),
                          }),
                          winner: CANDIDATES[row.strategic]?.name ?? '—',
                          rank: t(`play.ord.${yourRankOf(you, row.strategic) || 1}`),
                          instead: t(`play.ord.${sincereRank || 1}`),
                        })
                      : t('play.verdict.payless')
                    : row.sincere < 0
                      ? t('play.verdict.tied', { n: bloc })
                      : row.sincere !== row.abstain
                        ? t('play.verdict.moved', {
                            n: bloc,
                            winner: CANDIDATES[row.sincere]?.name ?? '—',
                            was: CANDIDATES[row.abstain]?.name ?? '—',
                          })
                        : t(bloc === 1 ? 'play.verdict.alone' : 'play.verdict.notYet', { n: bloc })}
              </p>

              <dl className="mt-3 flex flex-col gap-1.5 border-t border-dashed border-border pt-3">
                <div className="flex items-baseline gap-2.5">
                  <dd
                    data-testid="play-toflip"
                    className="w-10 shrink-0 text-right font-mono text-2xl font-bold leading-none tabular-nums text-primary"
                  >
                    {toFlip || '—'}
                  </dd>
                  <dt className="text-xs leading-snug text-muted-foreground">
                    {toFlip
                      ? t('play.count.toFlip', { method: ruleLabels[activeRule] })
                      : sincereRank === 1
                        ? t('play.count.already')
                        : t('play.count.noFlip', { max: MAX_BLOC })}
                  </dt>
                </div>
                <div className="flex items-baseline gap-2.5">
                  <dd
                    data-testid="play-totempt"
                    className="w-10 shrink-0 text-right font-mono text-2xl font-bold leading-none tabular-nums text-[var(--color-stamp)]"
                  >
                    {toTempt || '—'}
                  </dd>
                  <dt className="text-xs leading-snug text-muted-foreground">
                    {toTempt ? t('play.count.toTempt') : t('play.count.noTempt')}
                  </dt>
                </div>
              </dl>
            </section>

            {/* ── Where you stand in the crowd — hand-tally of first choices ── */}
            <section className="mt-7">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                {t('play.crowd.kicker')}
              </p>
              <h2 className="mt-0.5 font-display text-xl font-bold tracking-tight">
                {t('play.crowd.title')}
              </h2>
              <div
                data-testid="play-crowd"
                className="mt-3 rounded-xl border border-border bg-card p-4 sm:p-5"
              >
                <div className="flex flex-col gap-2.5">
                  {CANDIDATES.map((c, i) => {
                    const base = ELECTORATE_FIRST_CHOICE[i];
                    const mine = i === myFav ? bloc : 0;
                    const isLeader = i === leader;
                    return (
                      <div key={c.name} className="flex items-start gap-3">
                        <div className="flex w-28 shrink-0 items-center gap-1.5 pt-0.5 sm:w-32">
                          <span
                            aria-hidden
                            className="h-2.5 w-2.5 shrink-0 rounded-full"
                            style={{ background: candidateColor(i) }}
                          />
                          <span className="truncate text-sm">{c.name}</span>
                          <span
                            className={cn(
                              'ml-auto font-mono text-sm tabular-nums',
                              isLeader ? 'font-bold text-foreground' : 'text-muted-foreground'
                            )}
                          >
                            {base + mine}
                          </span>
                        </div>
                        <div className="flex flex-1 flex-wrap content-start gap-1 pt-1">
                          {Array.from({ length: base }, (_, k) => (
                            <span
                              key={`b${k}`}
                              aria-hidden
                              className="h-2.5 w-2.5 rounded-full opacity-45"
                              style={{ background: candidateColor(i) }}
                            />
                          ))}
                          {Array.from({ length: mine }, (_, k) => (
                            <span
                              key={`m${k}`}
                              aria-hidden
                              title={k === 0 ? t('play.crowd.you') : t('play.crowd.likeYou')}
                              className={cn(
                                'h-2.5 w-2.5 rounded-full bg-[var(--color-stamp)] ring-1 ring-[var(--color-stamp)]',
                                k === 0 && 'ring-2'
                              )}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <p
                  data-testid="play-crowd-caption"
                  aria-live="polite"
                  className="mt-4 border-t border-border pt-3 text-sm leading-relaxed text-muted-foreground"
                >
                  {t('play.crowd.stand', {
                    fav: CANDIDATES[myFav]?.name ?? '—',
                    camp: camps[myFav],
                    total: totalVoters,
                    leader: CANDIDATES[leader]?.name ?? '—',
                    leaderN: camps[leader],
                  })}{' '}
                  {leader === myFav ? (
                    <span className="font-medium text-primary">{t('play.crowd.youLead')}</span>
                  ) : (
                    <span>{t('play.crowd.squeeze')}</span>
                  )}
                </p>
              </div>
            </section>

            {/* ── How each method would count your sealed ballot ── */}
            <section className="mt-7">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                {t('play.allowsKicker')}
              </p>
              <h2 className="mt-0.5 flex items-center gap-2 font-display text-xl font-bold tracking-tight">
                {t('play.allowsTitle')}
                <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-xs font-semibold text-primary">
                  {rules.length}
                </span>
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{t('play.allowsHint')}</p>

              <div data-testid="play-methods" className="mt-3 flex flex-wrap gap-1.5">
                {perRule.map((r) => {
                  const w =
                    posture === 'abstain'
                      ? r.abstain
                      : posture === 'strategic'
                        ? r.strategic
                        : r.sincere;
                  const on = r.rule === activeRule;
                  return (
                    <button
                      key={r.rule}
                      type="button"
                      data-testid={`play-rule-${r.rule}`}
                      aria-pressed={on}
                      title={r.pays ? t('play.chipPays') : undefined}
                      onClick={() => setRule(r.rule)}
                      className={cn(
                        'flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors',
                        on
                          ? 'border-primary bg-primary/10 text-foreground ring-1 ring-primary'
                          : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                      )}
                    >
                      {r.pays && (
                        <span
                          aria-hidden
                          className="h-3.5 w-[2px] shrink-0 bg-[var(--color-stamp)]"
                        />
                      )}
                      {ruleLabels[r.rule]}
                      {w >= 0 && (
                        <span
                          className="rounded px-1 font-mono text-[0.62rem] font-bold"
                          style={{ color: candidateColor(w), background: `${candidateColor(w)}18` }}
                        >
                          {CANDIDATES[w].name}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              <p data-testid="play-pays-count" className="mt-2.5 text-sm text-muted-foreground">
                <span
                  aria-hidden
                  className="mr-1.5 inline-block h-3 w-[2px] translate-y-[2px] bg-[var(--color-stamp)]"
                />
                {rules.length === 1
                  ? t(paysCount > 0 ? 'play.paysSoleYes' : 'play.paysSoleNo')
                  : paysCount > 0
                    ? t('play.paysSome', { n: paysCount, total: rules.length })
                    : t('play.paysNone', { total: rules.length })}
              </p>
            </section>

            {/* ── The count itself, step by step — nothing hidden ── */}
            <section className="mt-7">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                <Term id="depouillement">{t('play.depouille.kicker')}</Term>
              </p>
              <h2 className="mt-0.5 font-display text-xl font-bold tracking-tight">
                {t('play.depouille.title', { method: ruleLabels[activeRule] })}
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                {t('play.depouille.hint')}
              </p>
              <DepouillementPanel trace={trace} candidates={CANDIDATES} />
              <BallotRegister
                ranks={tally.ranks}
                scores={tally.scores}
                lang={lang}
                mineFrom={mineFrom}
                candidates={CANDIDATES}
              />
            </section>

            {/* ── The result, and what it means for YOU ── */}
            <section
              aria-live="polite"
              className="mt-5 flex flex-col gap-4 rounded-xl border border-primary/30 bg-card p-5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
                  {t('play.electedWith', { method: ruleLabels[activeRule] })}
                </p>
                <p className="mt-1 flex items-center gap-3">
                  <span
                    data-testid="play-winner"
                    className="font-display text-3xl font-bold"
                    style={winner >= 0 ? { color: candidateColor(winner) } : undefined}
                  >
                    {CANDIDATES[winner]?.name ?? '—'}
                  </span>
                  {winner >= 0 && (
                    <span className="-rotate-6 rounded border-2 border-[var(--color-stamp)] px-2 py-0.5 font-mono text-[0.66rem] font-bold uppercase tracking-[0.18em] text-[var(--color-stamp)]">
                      {t('play.stamp')}
                    </span>
                  )}
                </p>
              </div>

              <div className="sm:text-right">
                <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
                  {t('play.youGetKicker')}
                </p>
                <p
                  data-testid="play-yourank"
                  className={cn(
                    'mt-1 font-display text-2xl font-bold',
                    myRank === 1
                      ? 'text-primary'
                      : myRank >= CANDIDATES.length
                        ? 'text-[var(--color-stamp)]'
                        : 'text-foreground'
                  )}
                >
                  {winner < 0 ? t('play.tie') : t(`play.ord.${myRank}`)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {posture === 'sincere'
                    ? t('play.youGetHint')
                    : t('play.vsSincere', {
                        rank: sincereRank ? t(`play.ord.${sincereRank}`) : t('play.tie'),
                      })}
                </p>
              </div>
            </section>

            {/* ── The weight: what actually decides an election is the margin ── */}
            <section className="mt-7">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                <Term id="pivotality">{t('play.weight.kicker')}</Term>
              </p>
              <h2 className="mt-0.5 font-display text-xl font-bold tracking-tight">
                {t('play.weight.title')}
              </h2>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
                {t('play.weight.lede', { n: num.format(BIG_N) })}
              </p>

              <div className="mt-4 rounded-xl border border-border bg-card p-4 sm:p-5">
                <label className="flex flex-col gap-1.5">
                  <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <span className="text-xs text-muted-foreground">{t('play.weight.knob')}</span>
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      {t('play.weight.gap', { margin: num.format(margin) })}
                    </span>
                  </span>
                  <input
                    data-testid="play-margin"
                    type="range"
                    min={0}
                    max={100}
                    value={sliderAt(margin)}
                    aria-label={t('play.weight.knob')}
                    onChange={(e) => {
                      markWeight();
                      setMargin(marginAt(Number(e.target.value)));
                    }}
                  />
                </label>

                <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border pt-4 sm:grid-cols-2">
                  <div>
                    <p
                      data-testid="play-share"
                      className="font-mono text-3xl font-bold leading-none tabular-nums text-primary"
                    >
                      {pct(margin / BIG_N)}
                    </p>
                    <p className="mt-1.5 text-xs leading-snug text-muted-foreground">
                      {t('play.weight.shareHint')}
                    </p>
                  </div>
                  <div>
                    <p
                      data-testid="play-convince"
                      className="font-mono text-3xl font-bold leading-none tabular-nums text-[var(--color-stamp)]"
                    >
                      {num.format(Math.ceil(margin / 2))}
                    </p>
                    <p className="mt-1.5 text-xs leading-snug text-muted-foreground">
                      {t('play.weight.convinceHint')}
                    </p>
                  </div>
                </div>

                {toFlip > 0 && (
                  <p
                    data-testid="play-bridge"
                    className="mt-4 border-t border-dashed border-border pt-3 text-xs leading-relaxed text-muted-foreground"
                  >
                    {t('play.weight.bridge', {
                      method: ruleLabels[activeRule],
                      k: toFlip,
                      n: VOTER_COUNT + bloc,
                      here: pct(toFlip / (VOTER_COUNT + bloc)),
                      there: pct(margin / BIG_N),
                    })}
                  </p>
                )}

                <button
                  type="button"
                  data-testid="play-florida"
                  onClick={() => {
                    markWeight();
                    setMargin(FLORIDA.margin);
                  }}
                  className={cn(
                    'mt-4 flex w-full items-start gap-2.5 rounded-lg border p-3 text-left text-xs leading-relaxed transition-colors',
                    margin === FLORIDA.margin
                      ? 'border-[var(--color-stamp)] bg-[var(--color-stamp)]/5 text-foreground'
                      : 'border-dashed border-border text-muted-foreground hover:border-[var(--color-stamp)]/50 hover:text-foreground'
                  )}
                >
                  <span
                    aria-hidden
                    className="mt-0.5 h-4 w-[2px] shrink-0 bg-[var(--color-stamp)]"
                  />
                  <span>
                    {t('play.weight.florida', {
                      margin: num.format(FLORIDA.margin),
                      total: num.format(FLORIDA.total),
                      share: pct(FLORIDA.margin / FLORIDA.total),
                      convince: num.format(Math.ceil(FLORIDA.margin / 2)),
                    })}
                    {margin !== FLORIDA.margin && (
                      <span className="ml-1 font-medium text-[var(--color-stamp)]">
                        {t('play.weight.floridaBack')}
                      </span>
                    )}
                  </span>
                </button>
              </div>

              <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {t('play.weight.oneOverN')}
              </p>
            </section>
          </>
        )}
      </div>
    </div>
  );
};

export default AVousDeJouerPage;
