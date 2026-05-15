import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from '../../hooks/useIsMobile';

const STYLE_ID = 'responsive-table-styles';

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
  const [showHint, setShowHint]   = useState(false);
  const isMobile                  = useIsMobile();

  useEffect(() => {
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = `
        .rsp-table thead th:first-child,
        .rsp-table tbody td:first-child,
        .rsp-table tfoot td:first-child {
          position: sticky; left: 0;
          background-color: var(--bs-table-bg, var(--bs-body-bg, white));
          z-index: 2; box-shadow: 2px 0 4px rgba(0,0,0,0.06);
        }
        .rsp-table thead th:first-child { z-index: 3; }
        @media (max-width: 767px) {
          .rsp-table table th, .rsp-table table td {
            padding: 0.25rem 0.35rem; font-size: 0.8rem;
          }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const check = () => setShowHint(el.scrollWidth > el.clientWidth + 4);
    check();

    const ro = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(check)
      : null;
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
        <div className="rsp-table">
          {children}
        </div>
      </div>

      {showHint && isMobile && (
        <div
          className="text-center text-muted"
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
