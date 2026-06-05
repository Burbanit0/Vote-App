import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

// ── Supported metrics ─────────────────────────────────────────────────────────

export type MetricKey =
  | 'bayesian_regret'
  | 'method_agreement'
  | 'winner_stability'
  | 'condorcet_compliance'
  | 'manipulability'
  | 'blank_rate'
  | 'stability_score'
  | 'majority_satisfaction'
  | 'delta_agreement';

interface Props {
  metric: MetricKey;
  size?: 'sm' | 'md';
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

// Tailwind-migrated (Phase 6): react-bootstrap Overlay/Popover → an absolutely
// positioned popover div (closes on outside click; placement controls anchor).

const POS: Record<NonNullable<Props['placement']>, string> = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'right-full top-1/2 mr-2 -translate-y-1/2',
  right: 'left-full top-1/2 ml-2 -translate-y-1/2',
};

const MetricTooltip: React.FC<Props> = ({
  metric,
  size = 'sm',
  placement = 'top',
  className = '',
}) => {
  const { t } = useTranslation();
  const [show, setShow] = React.useState(false);
  const targetRef = useRef<HTMLButtonElement>(null);
  const wrapRef = useRef<HTMLSpanElement>(null);

  const title = t(`metrics.${metric}.title`);
  const simple = t(`metrics.${metric}.simple`);
  const example = t(`metrics.${metric}.example`, { defaultValue: '' });
  const formula = t(`metrics.${metric}.formula`, { defaultValue: '' });
  const interpretation = t(`metrics.${metric}.interpretation`, { defaultValue: '' });

  // Close on outside click
  const handleClickOutside = React.useCallback((e: MouseEvent) => {
    if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
      setShow(false);
    }
  }, []);

  React.useEffect(() => {
    if (show) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [show, handleClickOutside]);

  return (
    <span ref={wrapRef} className="relative inline-block" data-style="tailwind">
      <button
        ref={targetRef}
        type="button"
        className={cn(
          'inline-flex shrink-0 cursor-pointer items-center border-0 bg-transparent px-0.5 align-middle leading-none text-muted-foreground',
          className
        )}
        style={{ fontSize: size === 'md' ? '1rem' : '0.72rem' }}
        aria-label={`${t('metrics.info')}: ${title}`}
        aria-expanded={show}
        onClick={(e) => {
          e.stopPropagation();
          setShow((s) => !s);
        }}
        data-testid={`metric-tooltip-${metric}`}
      >
        ⓘ
      </button>

      {show && (
        <div
          role="tooltip"
          id={`metric-pop-${metric}`}
          className={cn(
            'absolute z-[1060] w-[320px] max-w-[320px] rounded-md border border-border bg-popover text-popover-foreground shadow-lg',
            POS[placement]
          )}
        >
          <div className="border-b border-border px-3.5 py-2 text-[0.85rem] font-semibold">
            {title}
          </div>
          <div className="px-3.5 py-2.5 text-[0.8rem]">
            <p className="mb-2">{simple}</p>
            {example && (
              <p className="mb-2 text-[0.77rem] italic text-muted-foreground">{example}</p>
            )}
            {formula && (
              <code className="mb-2 block whitespace-pre-wrap rounded bg-muted px-2 py-1 text-[0.72rem]">
                {formula}
              </code>
            )}
            {interpretation && (
              <p className="mb-0 mt-0.5 border-t border-border pt-1.5 text-[0.75rem] text-muted-foreground">
                {interpretation}
              </p>
            )}
          </div>
        </div>
      )}
    </span>
  );
};

export default MetricTooltip;
