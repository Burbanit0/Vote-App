import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { usePlaygroundCtx } from './PlaygroundController';
import { MOMENTS, type MomentId } from './MomentRail';

// GuidedFooter — the guided fil. Walks the moments in order (simple → complex),
// one sentence at a time, with prev/next. It drives the SAME instrument as free
// browsing; the rail above still lets you jump anywhere. On the last moment, next
// loops back to the start so the journey can be replayed.
const ORDER: MomentId[] = MOMENTS.map((m) => m.id);

const GuidedFooter: React.FC = () => {
  const { activeMoment, setActiveMoment } = usePlaygroundCtx();
  const { t } = useTranslation('playground');
  const idx = ORDER.indexOf(activeMoment);
  const current = MOMENTS[idx];
  const prev = idx > 0 ? MOMENTS[idx - 1] : null;
  const next = idx < MOMENTS.length - 1 ? MOMENTS[idx + 1] : null;
  const isLast = idx === MOMENTS.length - 1;

  return (
    <div
      data-testid="guided-footer"
      className="mt-6 flex flex-col gap-2 rounded-lg border border-primary/15 bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <Button
        data-testid="guided-prev"
        variant="outline"
        size="sm"
        disabled={!prev}
        onClick={() => prev && setActiveMoment(prev.id)}
        className="shrink-0"
      >
        ← {prev ? t(`moments.${prev.id}.label`) : t('guided.start')}
      </Button>

      <div className="flex min-w-0 flex-1 flex-col items-center gap-1 px-2 text-center">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1" aria-hidden>
            {MOMENTS.map((m, i) => (
              <span
                key={m.id}
                className={cn(
                  'h-1.5 w-1.5 rounded-full',
                  i === idx ? 'bg-primary' : i < idx ? 'bg-primary/40' : 'bg-border'
                )}
              />
            ))}
          </span>
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted-foreground">
            {t('guided.moment', { n: current.n, total: MOMENTS.length })}
          </span>
        </div>
        <p className="truncate text-sm text-muted-foreground">
          <span className="font-display font-medium text-foreground">
            {t(`moments.${current.id}.label`)}
          </span>
          {' — '}
          {t(`moments.${current.id}.hint`)}
        </p>
      </div>

      <Button
        data-testid="guided-next"
        variant={isLast ? 'outline' : 'primary'}
        size="sm"
        onClick={() => setActiveMoment((next ?? MOMENTS[0]).id)}
        className="shrink-0"
      >
        {isLast ? t('guided.restart') : t('guided.next', { label: t(`moments.${next?.id}.label`) })}
      </Button>
    </div>
  );
};

export default GuidedFooter;
