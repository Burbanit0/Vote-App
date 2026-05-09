import React, { useEffect, useRef, useState } from 'react';
import { useIsMobile } from '../../hooks/useIsMobile';

// ── Inject sticky-column + compact-mobile CSS once ─────────────────────────

const STYLE_ID = 'responsive-table-styles';

if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    /* Sticky first column */
    .rsp-table thead th:first-child,
    .rsp-table tbody td:first-child,
    .rsp-table tfoot td:first-child {
      position: sticky;
      left: 0;
      background-color: white;
      z-index: 2;
      box-shadow: 2px 0 4px rgba(0, 0, 0, 0.06);
    }
    .rsp-table thead th:first-child {
      z-index: 3; /* above body cells */
    }

    /* Compact layout on mobile — equivalent to Bootstrap table-sm */
    @media (max-width: 767px) {
      .rsp-table table th,
      .rsp-table table td {
        padding: 0.25rem 0.35rem;
        font-size: 0.8rem;
      }
    }
  `;
  document.head.appendChild(style);
}

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  children: React.ReactNode;
  className?: string;
}

/**
 * Responsive table wrapper.
 *
 * - Horizontal scroll with touch-friendly momentum scrolling on iOS
 * - First column sticky (header + body + footer cells)
 * - Compact font/padding on mobile (< 768 px)
 * - "← Faites défiler →" hint shown when the table overflows its container
 */
const ResponsiveTable: React.FC<Props> = ({ children, className }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [showHint, setShowHint] = useState(false);
  const isMobile = useIsMobile();

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const check = () => setShowHint(el.scrollWidth > el.clientWidth + 4);
    check();

    // Re-check when content or viewport size changes
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
        className={className}
        style={{
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch' as any,
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
          ← Faites défiler →
        </div>
      )}
    </>
  );
};

export default ResponsiveTable;
