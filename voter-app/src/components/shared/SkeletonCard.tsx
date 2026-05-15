import React from 'react';
import { useTranslation } from 'react-i18next';

// Inject CSS animation once at module load
const STYLE_ID = 'skeleton-card-styles';
if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
  const s = document.createElement('style');
  s.id = STYLE_ID;
  s.textContent = `
    @keyframes skeleton-pulse {
      0%   { opacity: 1; }
      50%  { opacity: 0.45; }
      100% { opacity: 1; }
    }
    .skeleton-pulse {
      animation: skeleton-pulse 1.6s ease-in-out infinite;
    }
    .skeleton-line {
      background-color: var(--bs-border-color, #dee2e6);
      border-radius: 4px;
    }
  `;
  document.head.appendChild(s);
}

// ── SkeletonLine ────────────────────────────────────────────────────────────

const SkeletonLine: React.FC<{ width?: string; height?: number }> = ({
  width = '100%',
  height = 12,
}) => (
  <div
    className="skeleton-line"
    style={{ width, height, marginBottom: 10 }}
    aria-hidden="true"
  />
);

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
      className="skeleton-pulse rounded border"
      style={{ width, height, backgroundColor: 'var(--bs-secondary-bg, #f8f9fa)', padding: '0.75rem', overflow: 'hidden' }}
      role="status"
      aria-label={t('common.loading')}
    >
    {/* Card header simulation */}
    <SkeletonLine width="55%" height={16} />
    <div style={{ height: 1, backgroundColor: '#dee2e6', margin: '10px 0 14px' }} />
    {/* 3 text lines with varying widths */}
    <SkeletonLine width="90%" />
    <SkeletonLine width="75%" />
    <SkeletonLine width="82%" />
  </div>
  );
};

export default SkeletonCard;
