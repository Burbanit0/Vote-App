import React from 'react';
import { useTranslation } from 'react-i18next';
import InfoPopover from './InfoPopover';

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
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

// The ⓘ affordance itself (button, popover, outside-click, placement) is
// InfoPopover's job; this component is the metric's i18n content. Every string
// but the title is optional, so a metric can carry as much or as little
// explanation as its locale entry has.

const MetricTooltip: React.FC<Props> = ({ metric, placement = 'top', className }) => {
  const { t } = useTranslation();

  const title = t(`metrics.${metric}.title`);
  const simple = t(`metrics.${metric}.simple`);
  const example = t(`metrics.${metric}.example`, { defaultValue: '' });
  const formula = t(`metrics.${metric}.formula`, { defaultValue: '' });
  const interpretation = t(`metrics.${metric}.interpretation`, { defaultValue: '' });

  return (
    <InfoPopover
      testid={`metric-${metric}`}
      ariaLabel={`${t('metrics.info')}: ${title}`}
      placement={placement}
      className={className}
    >
      <div className="mb-2 border-b border-border pb-1.5 text-[0.85rem] font-semibold">{title}</div>
      <p className="mb-2 text-[0.8rem]">{simple}</p>
      {example && <p className="mb-2 text-[0.77rem] italic text-muted-foreground">{example}</p>}
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
    </InfoPopover>
  );
};

export default MetricTooltip;
