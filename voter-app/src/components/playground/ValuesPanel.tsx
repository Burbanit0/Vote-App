import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { paretoSplit, spotlight, type LensItem } from '../../lib/scorecard';
import MethodInfo from './MethodInfo';

// ValuesPanel (Lab reshape P5) — decide by your sensitivity, honestly.
// Step 1 (objective): strictly Pareto-dominated systems are ELIMINATED and shown
// struck through. Step 2 (values): the weight sliders merely SPOTLIGHT a point
// on the remaining trade-off frontier. The items keep a fixed order and carry no
// rank numbers — never a leaderboard.

export interface ValuesPanelProps {
  items: LensItem[];
  axisKeys: string[];
  axisLabels: Record<string, string>;
  itemLabels: Record<string, string>;
  weights: Record<string, number>;
  onWeightChange: (key: string, value: number) => void;
  /** FA-2: hide the per-axis sliders when the identity dial drives the weights. */
  granular?: boolean;
}

const ValuesPanel: React.FC<ValuesPanelProps> = ({
  items,
  axisKeys,
  axisLabels,
  itemLabels,
  weights,
  onWeightChange,
  granular = true,
}) => {
  const { t } = useTranslation('playground');
  const { frontier, dominated } = React.useMemo(
    () => paretoSplit(items, axisKeys),
    [items, axisKeys]
  );
  const dominatedIds = React.useMemo(() => new Set(dominated.map((d) => d.id)), [dominated]);
  const lit = React.useMemo(
    () => spotlight(frontier, weights, axisKeys),
    [frontier, weights, axisKeys]
  );

  return (
    <div data-testid="values-panel" className="flex flex-col gap-3">
      {/* Weights (not rendered while the identity dial drives them) */}
      {granular && (
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('values.weightsTitle')}
          </p>
          {axisKeys.map((k) => (
            <label key={k} className="flex items-center gap-2 text-xs">
              <span className="w-36 shrink-0 truncate text-muted-foreground" title={axisLabels[k]}>
                {axisLabels[k] ?? k}
              </span>
              <input
                data-testid={`weight-${k}`}
                type="range"
                className="flex-1"
                min={0}
                max={1}
                step={0.05}
                value={weights[k] ?? 0.5}
                onChange={(e) => onWeightChange(k, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
      )}

      {/* Systems — fixed order, no rank numbers */}
      <div className="flex flex-col gap-1.5">
        {items.map((it) => {
          const isDominated = dominatedIds.has(it.id);
          const isLit = it.id === lit;
          return (
            <div
              key={it.id}
              data-testid={`lens-item-${it.id}`}
              className={cn(
                'rounded-md border px-2.5 py-1.5 text-sm transition-colors',
                isDominated && 'border-border/60 text-muted-foreground line-through',
                !isDominated && !isLit && 'border-border',
                isLit && 'border-primary ring-1 ring-primary'
              )}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-0.5">
                  {itemLabels[it.id] ?? it.id}
                  <MethodInfo method={it.id} placement="left" />
                </span>
                {isDominated ? (
                  <span className="text-[0.68rem] no-underline">{t('values.dominated')}</span>
                ) : isLit ? (
                  <span className="text-[0.68rem] font-semibold text-primary">
                    ★ {t('values.spotlight')}
                  </span>
                ) : (
                  <span className="text-[0.68rem] text-muted-foreground">
                    {t('values.onFrontier')}
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-[0.7rem] text-muted-foreground">{t('values.footer')}</p>
    </div>
  );
};

export default ValuesPanel;
