import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { candidateColor } from '../../lib/palette';
import { track } from '../../lib/analytics';
import { pipsFrom, type BallotLanguage } from '../../lib/ballotLanguages';
import type { NamedPt } from '../../lib/playgroundVoting';

// BallotRegister — the tally sheet: every ballot actually counted, one row each,
// in the language it was cast. This is the rawest transparency — the voter can add
// them up by hand and land on the same count the replay animates. Yours (and the
// voters who share your opinion) are tinted so you can find yourself in the pile.

const POINT_BUDGET = 10;

/** What one ballot wrote for candidate c, in the cast language. */
function cell(
  lang: BallotLanguage,
  rank: number[],
  score: number[],
  pips: number[],
  c: number
): string {
  switch (lang) {
    case 'one':
      return rank[0] === c ? '✗' : '';
    case 'rank':
      return String(rank.indexOf(c) + 1);
    case 'approve':
      return score[c] === 1 ? '✓' : '';
    case 'score':
      return String(Math.round((score[c] ?? 0) * 4) + 1);
    case 'points':
      return pips[c] ? String(pips[c]) : '';
  }
}

const BallotRegister: React.FC<{
  ranks: number[][];
  scores: number[][];
  lang: BallotLanguage;
  /** Index of the first ballot that is yours (you + those like you); === length if none. */
  mineFrom: number;
  candidates: NamedPt[];
}> = ({ ranks, scores, lang, mineFrom, candidates }) => {
  const { t } = useTranslation();
  const [open, setOpen] = React.useState(false);
  const n = ranks.length;
  const mine = n - mineFrom;

  return (
    <div className="mt-3">
      <button
        type="button"
        data-testid="play-register-toggle"
        aria-expanded={open}
        onClick={() =>
          setOpen((o) => {
            if (!o) track('play_register_opened', { lang });
            return !o;
          })
        }
        className="text-sm font-medium text-primary underline-offset-2 hover:underline"
      >
        {open ? t('play.register.hide') : t('play.register.show', { n })}
      </button>

      {open && (
        <div data-testid="play-register" className="mt-3">
          <p className="mb-2 text-xs leading-relaxed text-muted-foreground">
            {mine > 0
              ? t('play.register.note', { n, k: mine })
              : t('play.register.noteAbstain', { n })}
          </p>
          <div className="max-h-80 overflow-auto rounded-lg border border-border">
            <table className="w-full border-collapse text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border">
                  <th className="px-2 py-1.5 text-left font-mono text-[0.6rem] uppercase tracking-[0.12em] text-muted-foreground">
                    {t('play.register.ballot')}
                  </th>
                  {candidates.map((c, i) => (
                    <th key={c.name} className="px-2 py-1.5 text-center font-medium">
                      <span className="flex items-center justify-center gap-1">
                        <span
                          aria-hidden
                          className="h-2 w-2 rounded-full"
                          style={{ background: candidateColor(i) }}
                        />
                        <span className="truncate">{c.name}</span>
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ranks.map((rank, r) => {
                  const isMine = r >= mineFrom;
                  const pips = lang === 'points' ? pipsFrom(scores[r], POINT_BUDGET) : [];
                  return (
                    <tr
                      key={r}
                      data-testid={isMine ? 'play-register-mine' : undefined}
                      className="border-b border-border/50 last:border-0"
                      style={
                        isMine
                          ? {
                              background: 'color-mix(in srgb, var(--color-stamp) 10%, transparent)',
                            }
                          : undefined
                      }
                    >
                      <td
                        className={cn(
                          'whitespace-nowrap px-2 py-1 font-mono text-xs tabular-nums',
                          isMine
                            ? 'font-semibold text-[var(--color-stamp)]'
                            : 'text-muted-foreground'
                        )}
                      >
                        {isMine ? t('play.register.you') : r + 1}
                      </td>
                      {candidates.map((c, i) => {
                        const mark = cell(lang, rank, scores[r], pips, i);
                        return (
                          <td
                            key={c.name}
                            className="px-2 py-1 text-center font-mono tabular-nums"
                            style={mark ? { color: candidateColor(i) } : undefined}
                          >
                            {mark || <span className="text-border">·</span>}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default BallotRegister;
