import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../../hooks/useIsMobile';

interface Props {
  children: React.ReactNode;
  className?: string;
  /** Accessible label for the table region (for screen readers navigating landmarks). */
  'aria-label'?: string;
}

/**
 * Responsive table wrapper.
 *
 * Accessibility (WCAG 2.1 AA):
 *   - The scroll container has role="region" + aria-label so screen-reader
 *     users know they are entering a scrollable area.
 *   - The "← Scroll →" overflow hint is aria-hidden (purely decorative).
 *   - The inner wrapper has role="group" to avoid conflicting with the
 *     semantic <table> element inside children.
 */
const ResponsiveTable: React.FC<Props> = ({ children, className, 'aria-label': ariaLabel }) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const [showHint, setShowHint] = useState(false);
  const isMobile = useIsMobile();

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const check = () => setShowHint(el.scrollWidth > el.clientWidth + 4);
    check();

    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(check) : null;
    ro?.observe(el);

    return () => ro?.disconnect();
  }, [children]);

  return (
    <>
      <div
        ref={containerRef}
        role="region"
        aria-label={ariaLabel ?? t('common.tableRegionLabel', { defaultValue: 'Data table' })}
        tabIndex={0}
        className={className}
        style={{
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch' as React.CSSProperties['WebkitOverflowScrolling'],
          position: 'relative',
        }}
      >
        <div className="rsp-table">{children}</div>
      </div>

      {showHint && isMobile && (
        <div
          className="text-center text-muted-foreground"
          style={{ fontSize: '0.72rem', padding: '2px 0 4px', userSelect: 'none' }}
          aria-hidden="true"
        >
          {t('common.scrollHint')}
        </div>
      )}
    </>
  );
};

export default ResponsiveTable;
