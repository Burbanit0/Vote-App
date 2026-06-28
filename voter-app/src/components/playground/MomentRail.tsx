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
  return (
    <div
      data-testid="moment-rail"
      role="radiogroup"
      aria-label={t('moments.electorate.label')}
      className="grid grid-cols-2 gap-2 sm:flex sm:items-stretch"
    >
      {MOMENTS.map((m) => {
        const on = m.id === active;
        return (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={on}
            data-testid={`moment-${m.id}`}
            onClick={() => onSelect(m.id)}
            className={cn(
              'group relative flex min-w-0 flex-1 items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all',
              on
                ? 'border-primary/40 bg-card shadow-sm'
                : 'border-border bg-muted/30 hover:border-border hover:bg-card'
            )}
          >
            <span
              className={cn(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-md font-mono text-sm font-semibold tabular-nums transition-colors',
                on
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground group-hover:text-foreground'
              )}
            >
              {m.n}
            </span>
            <span
              className={cn(
                'min-w-0 truncate text-sm font-medium transition-colors',
                on
                  ? 'font-display text-foreground'
                  : 'text-muted-foreground group-hover:text-foreground'
              )}
            >
              {t(`moments.${m.id}.label`)}
            </span>
            {on && (
              <span
                aria-hidden
                className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-primary"
              />
            )}
          </button>
        );
      })}
    </div>
  );
};

export default MomentRail;
