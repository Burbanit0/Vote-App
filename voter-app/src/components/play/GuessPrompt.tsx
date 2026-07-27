import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { candidateColor } from '../../lib/palette';
import type { NamedPt } from '../../lib/playgroundVoting';

// GuessPrompt — the optional "devine d'abord" step, shown INSIDE the booth, before
// any result exists, so the reveal can't be peeked. Controlled: the page owns the
// guess and scores it against the engine winner once the vote is cast. Skipping is
// free — leaving it untouched just casts without a prediction.

const GuessPrompt: React.FC<{
  candidates: NamedPt[];
  value: number | null;
  onChange: (i: number) => void;
}> = ({ candidates, value, onChange }) => {
  const { t } = useTranslation();
  return (
    <section data-testid="play-guess" className="rounded-lg border border-dashed border-border p-3">
      <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
        {t('play.guess.kicker')}
      </p>
      <p className="mt-0.5 text-sm text-muted-foreground">{t('play.guess.prompt')}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {candidates.map((c, i) => (
          <button
            key={c.name}
            type="button"
            data-testid={`play-guess-${i}`}
            aria-pressed={value === i}
            onClick={() => onChange(i)}
            className={cn(
              'flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors',
              value === i
                ? 'font-semibold text-foreground'
                : 'border-border text-muted-foreground hover:text-foreground'
            )}
            style={
              value === i
                ? {
                    borderColor: candidateColor(i),
                    background: `color-mix(in srgb, ${candidateColor(i)} 12%, transparent)`,
                  }
                : undefined
            }
          >
            <span
              aria-hidden
              className="h-2 w-2 rounded-full"
              style={{ background: candidateColor(i) }}
            />
            {c.name}
          </button>
        ))}
      </div>
    </section>
  );
};

export default GuessPrompt;
