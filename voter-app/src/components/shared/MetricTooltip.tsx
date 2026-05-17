import React, { useRef } from 'react';
import { Overlay, Popover } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';

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
  metric:     MetricKey;
  size?:      'sm' | 'md';
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

const MetricTooltip: React.FC<Props> = ({
  metric,
  size       = 'sm',
  placement  = 'top',
  className  = '',
}) => {
  const { t }       = useTranslation();
  const [show, setShow] = React.useState(false);
  const targetRef   = useRef<HTMLButtonElement>(null);

  const title          = t(`metrics.${metric}.title`);
  const simple         = t(`metrics.${metric}.simple`);
  const example        = t(`metrics.${metric}.example`,        { defaultValue: '' });
  const formula        = t(`metrics.${metric}.formula`,        { defaultValue: '' });
  const interpretation = t(`metrics.${metric}.interpretation`, { defaultValue: '' });

  // Close on outside click
  const handleClickOutside = React.useCallback((e: MouseEvent) => {
    if (targetRef.current && !targetRef.current.contains(e.target as Node)) {
      setShow(false);
    }
  }, []);

  React.useEffect(() => {
    if (show) document.addEventListener('mousedown', handleClickOutside);
    return ()  => document.removeEventListener('mousedown', handleClickOutside);
  }, [show, handleClickOutside]);

  const iconStyle: React.CSSProperties = {
    fontSize:       size === 'md' ? '1rem' : '0.72rem',
    lineHeight:     1,
    color:          'var(--bs-secondary-color, #6c757d)',
    cursor:         'pointer',
    verticalAlign:  'middle',
    padding:        '0 2px',
    textDecoration: 'none',
    background:     'none',
    border:         'none',
    flexShrink:     0,
  };

  return (
    <>
      <button
        ref={targetRef}
        type="button"
        className={`btn-metric-tooltip ${className}`}
        style={iconStyle}
        aria-label={`${t('metrics.info')}: ${title}`}
        aria-expanded={show}
        onClick={(e) => { e.stopPropagation(); setShow((s) => !s); }}
        data-testid={`metric-tooltip-${metric}`}
      >
        ⓘ
      </button>

      <Overlay
        target={targetRef.current}
        show={show}
        placement={placement}
        rootClose
        onHide={() => setShow(false)}
      >
        <Popover id={`metric-pop-${metric}`} style={{ maxWidth: 320 }}>
          <Popover.Header as="div" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
            {title}
          </Popover.Header>
          <Popover.Body style={{ fontSize: '0.8rem', padding: '10px 14px' }}>
            {/* Simple definition */}
            <p className="mb-2">{simple}</p>

            {/* Concrete example */}
            {example && (
              <p className="text-muted mb-2" style={{ fontStyle: 'italic', fontSize: '0.77rem' }}>
                {example}
              </p>
            )}

            {/* Formula */}
            {formula && (
              <code
                className="d-block mb-2 px-2 py-1 rounded"
                style={{
                  fontSize:   '0.72rem',
                  background: 'var(--bs-secondary-bg, #f8f9fa)',
                  color:      'var(--bs-body-color)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {formula}
              </code>
            )}

            {/* Interpretation */}
            {interpretation && (
              <p
                className="mb-0"
                style={{
                  fontSize:   '0.75rem',
                  color:      'var(--bs-secondary-color, #6c757d)',
                  borderTop:  '1px solid var(--bs-border-color)',
                  paddingTop: 6,
                  marginTop:  2,
                }}
              >
                {interpretation}
              </p>
            )}
          </Popover.Body>
        </Popover>
      </Overlay>
    </>
  );
};

export default MetricTooltip;
