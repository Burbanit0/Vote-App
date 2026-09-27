import React from 'react';
import { useTranslation } from 'react-i18next';

// ── SkeletonLine ────────────────────────────────────────────────────────────

const SkeletonLine: React.FC<{ width?: string; height?: number }> = ({
  width = '100%',
  height = 12,
}) => <div className="mb-2.5 rounded bg-border" style={{ width, height }} aria-hidden="true" />;

// ── SkeletonCard ────────────────────────────────────────────────────────────

interface Props {
  /** Card height in px. Defaults to 180. */
  height?: number;
  /** Card width. Defaults to '100%'. */
  width?: string;
}

/**
 * Animated placeholder that mimics a Card with a header and 3 text lines.
 * Use while API data is loading to prevent layout shift.
 */
const SkeletonCard: React.FC<Props> = ({ height = 180, width = '100%' }) => {
  const { t } = useTranslation();
  return (
    <div
      className="animate-pulse overflow-hidden rounded border border-border bg-muted p-3 motion-reduce:animate-none"
      style={{ width, height }}
      role="status"
      aria-label={t('common.loading')}
    >
      {/* Card header simulation */}
      <SkeletonLine width="55%" height={16} />
      <div className="mb-3.5 mt-2.5 h-px bg-border" />
      {/* 3 text lines with varying widths */}
      <SkeletonLine width="90%" />
      <SkeletonLine width="75%" />
      <SkeletonLine width="82%" />
    </div>
  );
};

export default SkeletonCard;
