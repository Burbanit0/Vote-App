import React from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  message?: string;
  height?: number;
}

/**
 * SVG placeholder displayed in chart containers when no data is available.
 * Mimics a bar chart outline in muted Bootstrap grey.
 */
const EmptyChart: React.FC<Props> = ({
  message,
  height = 200,
}) => {
  const { t } = useTranslation();
  const displayMessage = message ?? t('common.emptyChart');
  return (
    <div
      className="d-flex flex-column align-items-center justify-content-center"
      style={{ height, gap: '0.75rem' }}
      role="img"
      aria-label={displayMessage}
    >
    <svg width={110} height={72} viewBox="0 0 110 72" aria-hidden="true">
      {/* Y axis */}
      <line x1={8} y1={6} x2={8} y2={64} stroke="var(--bs-border-color, #dee2e6)" strokeWidth={1.5} />
      {/* Baseline */}
      <line x1={6} y1={64} x2={106} y2={64} stroke="var(--bs-border-color, #dee2e6)" strokeWidth={1.5} />
      {/* Bars */}
      {[
        { x: 12, h: 22 },
        { x: 27, h: 42 },
        { x: 42, h: 30 },
        { x: 57, h: 52 },
        { x: 72, h: 18 },
        { x: 87, h: 36 },
      ].map(({ x, h }) => (
        <rect
          key={x}
          x={x}
          y={64 - h}
          width={13}
          height={h}
          fill="none"
          stroke="var(--bs-border-color, #dee2e6)"
          strokeWidth={1.5}
          rx={2}
        />
      ))}
    </svg>

    <p className="text-muted mb-0" style={{ fontSize: '0.85rem', textAlign: 'center', maxWidth: 260 }}>
      {displayMessage}
    </p>
  </div>
  );
};

export default EmptyChart;
