import React, { useRef, useState } from 'react';
import { Overlay, Tooltip } from 'react-bootstrap';
import { useMethodCons, useMethodLabels, useMethodPros } from '../Simulation/simulationConstants';
import { METHOD_DESCRIPTIONS } from '../Simulation/simulationConstants';

interface Props {
  method: string;
  children?: React.ReactNode;
}

/**
 * Wraps a method name in an accessible tooltip.
 *
 * Keyboard behaviour (WCAG 2.1 SC 2.1.1):
 *   - Tab        → focuses the trigger
 *   - Enter / Space → toggles the tooltip
 *   - Escape     → closes the tooltip and returns focus
 */
const MethodTooltip: React.FC<Props> = ({ method, children }) => {
  const methodLabels = useMethodLabels();
  const methodPros   = useMethodPros();
  const methodCons   = useMethodCons();

  const label       = children ?? methodLabels[method] ?? method;
  const description = METHOD_DESCRIPTIONS[method];
  const pro         = methodPros[method];
  const con         = methodCons[method];

  const [show, setShow]   = useState(false);
  const triggerRef        = useRef<HTMLSpanElement>(null);

  if (!description) return <span>{label}</span>;

  const open  = () => setShow(true);
  const close = () => setShow(false);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setShow((prev) => !prev);
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      triggerRef.current?.blur();
    }
  };

  const tooltipContent = (
    <Tooltip id={`tip-${method}`} style={{ maxWidth: 300 }}>
      <div className="text-start p-1" style={{ fontSize: '0.82rem' }}>
        <div className="fw-bold mb-1" style={{ fontSize: '0.9rem' }}>
          {methodLabels[method] ?? method}
        </div>
        <div className="mb-2" style={{ lineHeight: 1.45, color: '#dee2e6' }}>
          {description}
        </div>
        {pro && (
          <div style={{ color: '#a8d5a2' }}>
            <span className="fw-semibold" aria-hidden="true">✓ </span>{pro}
          </div>
        )}
        {con && (
          <div style={{ color: '#f5a5a5', marginTop: 3 }}>
            <span className="fw-semibold" aria-hidden="true">✗ </span>{con}
          </div>
        )}
      </div>
    </Tooltip>
  );

  return (
    <>
      <span
        ref={triggerRef}
        tabIndex={0}
        role="button"
        aria-label={`${methodLabels[method] ?? method} — definition`}
        aria-expanded={show}
        aria-haspopup="true"
        style={{
          cursor: 'help',
          borderBottom: '1px dashed #adb5bd',
          display: 'inline',
          outline: 'none',
        }}
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        onKeyDown={handleKeyDown}
        onClick={() => setShow((prev) => !prev)}
      >
        {label}
      </span>

      <Overlay
        target={triggerRef.current}
        show={show}
        placement="top"
      >
        {tooltipContent}
      </Overlay>
    </>
  );
};

export default MethodTooltip;
