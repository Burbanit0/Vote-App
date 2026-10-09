import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import type { NamedPt } from '../../lib/playgroundVoting';
import type { VoteTrace } from '../../lib/voteTrace';
import { explainWinner } from '../../lib/explainWinner';

// WinnerExplanation — the one plain sentence that names WHY the winner won, in
// the language of the method. Thin: all logic is in explainWinner (pure); this
// picks the locale and renders. Drop it wherever a finished VoteTrace exists.

const WinnerExplanation: React.FC<{
  trace: VoteTrace;
  candidates: NamedPt[];
  /** Names the method in the kicker, where several methods' winners sit side by side. */
  ruleLabel?: string;
  className?: string;
}> = ({ trace, candidates, ruleLabel, className }) => {
  const { t } = useTranslation('playground');
  const { key, params } = explainWinner(trace, candidates);
  // Names are plain text: React escapes them, so i18next must not as well.
  const raw = { interpolation: { escapeValue: false } };

  return (
    <div
      data-testid="winner-explanation"
      className={cn(
        'rounded-lg border-l-2 border-[var(--color-stamp)] bg-card/60 py-2 pl-3 pr-3',
        className
      )}
    >
      <p className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-muted-foreground">
        {ruleLabel ? t('explain.kickerRule', { rule: ruleLabel, ...raw }) : t('explain.kicker')}
      </p>
      <p className="mt-0.5 text-sm leading-relaxed text-foreground">
        {t(key, { ...params, ...raw })}
      </p>
    </div>
  );
};

export default WinnerExplanation;
