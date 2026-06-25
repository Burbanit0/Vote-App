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
    className="flex items-stretch gap-1 overflow-x-auto rounded-lg border border-border bg-card p-1"
  >
    {MOMENTS.map((m, i) => {
      const on = m.id === active;
      return (
        <React.Fragment key={m.id}>
          <button
            type="button"
            role="radio"
            aria-checked={on}
            data-testid={`moment-${m.id}`}
            onClick={() => onSelect(m.id)}
            className={cn(
              'flex min-w-0 flex-1 items-center gap-2 rounded-md px-3 py-2 text-left transition-colors',
              on ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent/50'
            )}
          >
            <span
              className={cn(
                'font-mono text-xs tabular-nums',
                on ? 'text-primary' : 'text-muted-foreground/60'
              )}
            >
              {m.n}
            </span>
            <span aria-hidden>{m.icon}</span>
            <span className={cn('min-w-0 truncate text-sm font-medium', on && 'font-display')}>
              {m.label}
            </span>
          </button>
          {i < MOMENTS.length - 1 && (
            <span
              aria-hidden
              className="hidden self-center px-0.5 text-muted-foreground/40 sm:block"
            >
              →
            </span>
          )}
        </React.Fragment>
      );
    })}
  </div>
);

export default MomentRail;
