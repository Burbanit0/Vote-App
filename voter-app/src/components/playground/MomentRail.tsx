import * as React from 'react';
import { cn } from '@/lib/utils';

// MomentRail — the spine of the single-instrument journey. Four "moments" from
// simple to complex, one active at a time. The others are not hidden in a drawer:
// their effect is already baked into the live instrument; the rail only swaps
// which knobs are in your hand. Reads as a strip of stations on the instrument.

export type MomentId = 'electorate' | 'method' | 'strategy' | 'campaign' | 'bilan';

export const MOMENTS: { id: MomentId; n: string; icon: string; label: string; hint: string }[] = [
  {
    id: 'electorate',
    n: '1',
    icon: '👥',
    label: 'Électorat',
    hint: 'Qui vote, comment il se distribue et se comporte.',
  },
  {
    id: 'method',
    n: '2',
    icon: '🗳',
    label: 'Méthode',
    hint: 'La règle de décompte et la forme du bulletin.',
  },
  {
    id: 'strategy',
    n: '3',
    icon: '♟',
    label: 'Stratégie',
    hint: 'Vote utile, vote blanc, manipulation.',
  },
  {
    id: 'campaign',
    n: '4',
    icon: '📈',
    label: 'Campagne',
    hint: 'La réaction du vote dans le temps.',
  },
  {
    id: 'bilan',
    n: '5',
    icon: '⚖',
    label: 'Bilan',
    hint: 'Le verdict — ce que ça vaut, selon vos valeurs.',
  },
];

interface MomentRailProps {
  active: MomentId;
  onSelect: (id: MomentId) => void;
}

const MomentRail: React.FC<MomentRailProps> = ({ active, onSelect }) => (
  <div
    data-testid="moment-rail"
    role="radiogroup"
    aria-label="Moment de l’exploration"
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
                : 'bg-background text-muted-foreground/70 group-hover:text-foreground'
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
            {m.label}
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

export default MomentRail;
