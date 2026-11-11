import * as React from 'react';
import type { LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';

/**
 * A choice between a few options, all in view: a track of equal segments with the
 * chosen one raised on a card that slides between them (the homepage's rule picker
 * does the same). A radiogroup: each segment says whether it is the one chosen.
 */
export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  icon?: LucideIcon;
  testid?: string;
}

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  const at = options.findIndex((o) => o.value === value);
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="relative grid rounded-lg bg-muted p-0.5"
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0.5 left-0.5 rounded-md bg-card shadow-sm ring-1 ring-border transition-transform duration-300 ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
        style={{
          width: `calc((100% - 4px) / ${options.length})`,
          transform: `translateX(${at * 100}%)`,
        }}
      />
      {options.map(({ value: v, label: text, icon: Icon, testid }) => {
        const on = v === value;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={on}
            data-testid={testid}
            onClick={() => !on && onChange(v)}
            className={cn(
              'relative flex items-center justify-center gap-1.5 rounded-md px-2.5 py-1.5 text-[0.8rem] font-semibold transition-colors',
              on ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {Icon && <Icon size={14} strokeWidth={1.75} aria-hidden />}
            {text}
          </button>
        );
      })}
    </div>
  );
}
