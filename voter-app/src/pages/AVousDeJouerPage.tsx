import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useMetaTags } from '../hooks/useMetaTags';
import { candidateColor } from '../lib/palette';
import { useVotingLabels } from '../hooks/useVotingLabels';
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
  bestResponse,
  pivot,
  winnerWith,
  yourRankOf,
  type Posture,
} from '../lib/votePlay';
import type { Rule } from '../lib/playgroundVoting';

// AVousDeJouerPage — you become one voter in a small, close election, and discover
// that the ballot LANGUAGE decides how much of your opinion is even allowed onto the
// paper — and therefore which counting methods exist at all.
//
// The signature is the ballot itself: one opinion, five papers. Your affinities stay
// put on the left; the paper on the right re-forms, and the marks are laid in the
// same terracotta ink as the "Élu" stamp and the /decouvrir tally strokes. The paper
// is a skin over real controls — the sliders are the input, the ballot is the read-out.
//
// The languages are a taxonomy, not a sequence, so they carry a glyph of the mark
// they actually make — never 01/02/03. Inside the ranked ballot, though, the numerals
// ARE the content.

const POINT_BUDGET = 10;

const POSTURES: Posture[] = ['sincere', 'strategic', 'abstain'];

// Each glyph is the mark that language actually leaves on paper.
const GLYPH: Record<BallotLanguage, React.ReactNode> = {
  one: <span className="font-mono text-sm font-bold">✗</span>,
  rank: <span className="font-mono text-[0.6rem] font-bold tracking-tight">1·2·3</span>,
  approve: <span className="font-mono text-sm font-bold">✓✓</span>,
  score: <span className="font-mono text-[0.6rem] font-bold tracking-tight">1–5</span>,
  points: <span className="font-mono text-[0.7rem] leading-none">●●●</span>,
};

// A labelled knob inside the ballot — rendered ONLY where the language forces a
// tactical decision, so its very presence is the message: on this paper, "sincere"
// does not determine what you write.
const KnobRow: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="mt-3 flex flex-col gap-1 border-t border-dashed border-border pt-2.5">
    <span className="text-[0.7rem] font-medium text-[var(--color-stamp)]">{label}</span>
    {children}
  </div>
);

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

const AVousDeJouerPage: React.FC = () => {
  const { t } = useTranslation();
  const { ruleLabels } = useVotingLabels();

  // Your opinion — the one thing that does NOT change when the paper does.
  const [you, setYou] = React.useState<number[]>(DEFAULT_YOU);
  const [lang, setLang] = React.useState<BallotLanguage>('one');
  const [posture, setPosture] = React.useState<Posture>('sincere');
  // You, plus the voters who share your opinion. One ballot alone is almost never
  // pivotal — the honest question is how many of you it takes.
  const [bloc, setBloc] = React.useState(1);
  // The knobs that make "sincere" under-determined on cardinal papers.
  const [approveK, setApproveK] = React.useState(2);
  const [contrast, setContrast] = React.useState(1);
  const [concentration, setConcentration] = React.useState(1);

  useMetaTags({ title: `Vote Lab — ${t('play.title')}`, description: t('play.lede') });

  const opt: BallotOptions = { approveK, contrast, concentration, levels: 5 };
  const rules = RULES_FOR[lang];
  const [rule, setRule] = React.useState<Rule>(rules[0]);
  // Keep the selected method valid when the language closes doors under it.
  React.useEffect(() => {
    if (!RULES_FOR[lang].includes(rule)) setRule(RULES_FOR[lang][0]);
  }, [lang, rule]);
  const activeRule = rules.includes(rule) ? rule : rules[0];

  const myOrder = React.useMemo(() => orderOf(you), [you]);

  // One pass over the language's methods, for the three postures. `strategic` is a
  // per-rule best response: what serves you under Borda is not what serves you under
  // IRV — that difference IS the lesson, so it cannot be computed once for the page.
  const perRule = React.useMemo(() => {
    const sincereBallot = ballotFrom(you, lang, opt);
    return rules.map((rule) => {
      const best = bestResponse(you, lang, rule, opt, bloc);
      return {
        rule,
        sincereBallot,
        sincere: winnerWith(sincereBallot, lang, rule, bloc),
        strategic: best.winner,
        strategicBallot: best.ballot,
        abstain: winnerWith(null, lang, rule),
        pays: !best.sincereIsBest,
      };
    });
    // `opt` is rebuilt every render but its contents are exactly these three knobs.
  }, [you, lang, rules, bloc, approveK, contrast, concentration]);

  const row = perRule.find((r) => r.rule === activeRule) ?? perRule[0];
  const paysCount = perRule.filter((r) => r.pays).length;

  // The two counters, for the selected method only — the scan is the expensive part.
  const { toFlip, toTempt } = React.useMemo(
    () => pivot(you, lang, activeRule, opt),
    [you, lang, activeRule, approveK, contrast, concentration]
  );

  // The paper you are actually holding. Abstention has no paper at all.
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

  // What this language writes for candidate i — used both to draw the mark and to
  // spot where a tactical ballot departs from an honest one.
  const markOf = (b: Ballot, i: number): number =>
    lang === 'one'
      ? b.rank[0] === i
        ? 1
        : 0
      : lang === 'rank'
        ? b.rank.indexOf(i)
        : (b.score?.[i] ?? 0);

  const pips = React.useMemo(
    () => (ballot?.score ? pipsFrom(ballot.score, POINT_BUDGET) : []),
    [ballot]
  );

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

        <div className="mt-7 grid grid-cols-1 gap-5 lg:grid-cols-[19rem_minmax(0,1fr)]">
          {/* ── Your opinion — fixed across every language ── */}
          <section
            data-testid="play-opinion"
            className="h-fit rounded-xl border border-border bg-card p-4"
          >
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
              {t('play.opinionKicker')}
            </p>
            <h2 className="mt-0.5 font-display text-lg font-semibold">{t('play.opinionTitle')}</h2>
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
                      {Math.round(you[i] * 100)}
                    </span>
                  </span>
                  <input
                    data-testid={`play-affinity-${i}`}
                    type="range"
                    min={0}
                    max={100}
                    value={Math.round(you[i] * 100)}
                    aria-label={c.name}
                    onChange={(e) =>
                      setYou((prev) =>
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
              {myOrder.map((i) => CANDIDATES[i].name).join(' › ')}
            </p>
          </section>

          {/* ── The ballot: one opinion, five papers ── */}
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
                  const on = id === lang;
                  return (
                    <button
                      key={id}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      data-testid={`play-lang-${id}`}
                      onClick={() => setLang(id)}
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
                {t(`play.says.${lang}`)}
              </p>
            </div>

            {/* The paper itself — the marks are laid in the app's stamp ink. */}
            <div
              data-testid="play-ballot"
              className={cn(
                'relative mx-auto w-full max-w-[30rem] rotate-[-0.7deg] rounded-sm border bg-card px-5 py-4 shadow-md transition-opacity',
                posture === 'abstain'
                  ? 'border-dashed border-border opacity-55'
                  : 'border-primary/25'
              )}
            >
              <Corners />
              {posture === 'abstain' && (
                <span
                  data-testid="play-abstain-band"
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
                  // A tactical ballot that departs from the honest one, row by row.
                  const strayed =
                    !!ballot &&
                    posture === 'strategic' &&
                    markOf(ballot, i) !== markOf(row.sincereBallot, i);
                  return (
                    <li
                      key={c.name}
                      className="flex items-center justify-between gap-3 rounded px-1.5 py-1 text-sm"
                      style={
                        strayed
                          ? {
                              background: 'color-mix(in srgb, var(--color-stamp) 12%, transparent)',
                            }
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

                      {/* The mark this language leaves for this candidate. */}
                      <span
                        data-testid={`play-mark-${i}`}
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
                                    p < (pips[i] ?? 0)
                                      ? 'bg-[var(--color-stamp)]'
                                      : 'border border-border'
                                  )}
                                />
                              ))}
                            </span>
                            <span className="w-4 text-right text-xs tabular-nums">
                              {pips[i] ?? 0}
                            </span>
                          </span>
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>

              {/* The stub edge — the paper ends, it is not a panel. */}
              <div aria-hidden className="mt-3 border-b border-dashed border-border" />

              {/* The tactical knob — shown only where "sincere" is under-determined,
                  and only while you are the one filling the paper in. */}
              {posture === 'sincere' && lang === 'approve' && (
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
              {posture === 'sincere' && lang === 'score' && (
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
              {posture === 'sincere' && lang === 'points' && (
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
            </div>

            {/* ── How you fill it in: honestly, in your own interest, or not at all ── */}
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
                {t('play.posture.kicker')}
              </p>
              <div
                role="radiogroup"
                aria-label={t('play.posture.kicker')}
                className="mt-2 flex flex-wrap gap-1.5"
              >
                {POSTURES.map((p) => {
                  const on = p === posture;
                  return (
                    <button
                      key={p}
                      type="button"
                      role="radio"
                      aria-checked={on}
                      data-testid={`play-posture-${p}`}
                      onClick={() => setPosture(p)}
                      // No weight change on selection: it would re-flow the row and
                      // make the buttons jump under the pointer as you compare.
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

              {/* Your camp. A single ballot is almost never pivotal — saying so, and
                  then measuring what IS, is more honest than pretending otherwise. */}
              <label className="mt-3 flex flex-col gap-1 border-t border-border pt-3">
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

              {/* The two counters, stated plainly. This is the number people carry away. */}
              <dl className="mt-3 flex flex-col gap-1.5 border-t border-dashed border-border pt-3">
                <div className="flex items-baseline gap-2.5">
                  <dd
                    data-testid="play-toflip"
                    className="w-10 shrink-0 text-right font-mono text-2xl font-bold tabular-nums leading-none text-primary"
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
                    className="w-10 shrink-0 text-right font-mono text-2xl font-bold tabular-nums leading-none text-[var(--color-stamp)]"
                  >
                    {toTempt || '—'}
                  </dd>
                  <dt className="text-xs leading-snug text-muted-foreground">
                    {toTempt ? t('play.count.toTempt') : t('play.count.noTempt')}
                  </dt>
                </div>
              </dl>
            </div>
          </section>
        </div>

        {/* ── The doors this paper opens (and closes) ── */}
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
                  {/* The same ink bar as the legend below — one mark, one meaning. */}
                  {r.pays && (
                    <span aria-hidden className="h-3.5 w-[2px] shrink-0 bg-[var(--color-stamp)]" />
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
              {/* No stamp when the rule cannot separate them — an honest dead heat. */}
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
      </div>
    </div>
  );
};

export default AVousDeJouerPage;
