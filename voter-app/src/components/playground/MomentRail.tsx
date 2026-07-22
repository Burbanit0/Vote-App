import * as React from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Vote, Swords, TrendingUp, Scale, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

// MomentRail — the spine of the single-instrument journey. Five "moments" from
// simple to complex, one active at a time. The others are not hidden in a drawer:
// their effect is already baked into the live instrument; the rail only swaps
// which knobs are in your hand. Labels/hints come from the `playground` i18n
// namespace (moments.<id>.label / .hint).

export type MomentId = 'electorate' | 'method' | 'strategy' | 'campaign' | 'bilan';

export const MOMENTS: { id: MomentId; n: string; Icon: LucideIcon }[] = [
  { id: 'electorate', n: '1', Icon: Users },
  { id: 'method', n: '2', Icon: Vote },
  { id: 'strategy', n: '3', Icon: Swords },
  { id: 'campaign', n: '4', Icon: TrendingUp },
  { id: 'bilan', n: '5', Icon: Scale },
];

interface MomentRailProps {
  active: MomentId;
  onSelect: (id: MomentId) => void;
}

const MomentRail: React.FC<MomentRailProps> = ({ active, onSelect }) => {
  const { t } = useTranslation('playground');
  const activeIndex = MOMENTS.findIndex((m) => m.id === active);
  return (
    // A control sequence, not loose tabs: the numbered steps are wired by a lit
    // track that fills up to the step you're on — the simple→complex path made
    // visible. On mobile it falls back to a plain two-column grid (no track).
    <div
      data-testid="moment-rail"
      role="radiogroup"
      aria-label={t('moments.electorate.label')}
      className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-0"
    >
      {MOMENTS.map((m, i) => {
        const on = m.id === active;
        const done = i < activeIndex;
        return (
          <React.Fragment key={m.id}>
            {i > 0 && (
              <span
                aria-hidden
                className={cn(
                  'hidden h-px w-3 shrink-0 sm:block lg:w-6',
                  i <= activeIndex ? 'bg-primary/60' : 'bg-border'
                )}
              />
            )}
            <button
              type="button"
              role="radio"
              aria-checked={on}
              data-testid={`moment-${m.id}`}
              onClick={() => onSelect(m.id)}
              className={cn(
                'group flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-all',
                on
                  ? 'border border-primary/30 bg-card shadow-sm'
                  : 'border border-transparent hover:bg-muted/50'
              )}
            >
              <span
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-sm font-semibold tabular-nums transition-colors',
                  on
                    ? 'bg-primary text-primary-foreground ring-2 ring-primary/20'
                    : done
                      ? 'bg-primary/15 text-primary'
                      : 'border border-border bg-background text-muted-foreground group-hover:text-foreground'
                )}
              >
                {m.n}
              </span>
              <span
                className={cn(
                  'min-w-0 truncate text-sm transition-colors',
                  on
                    ? 'font-display font-semibold text-foreground'
                    : 'font-medium text-muted-foreground group-hover:text-foreground'
                )}
              >
                {t(`moments.${m.id}.label`)}
              </span>
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default MomentRail;
