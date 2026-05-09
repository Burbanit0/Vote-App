import React from 'react';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';
import {
  METHOD_CONS,
  METHOD_DESCRIPTIONS,
  METHOD_LABELS,
  METHOD_PROS,
} from '../Simulation/simulationConstants';

interface Props {
  method: string;
  children?: React.ReactNode;
}

/**
 * Wraps a method name in an accessible tooltip showing description, pro and con.
 *
 * Trigger: hover OR focus (keyboard-accessible) — works on desktop and touch
 * (mobile browsers fire a focus event on tap before activating the element).
 *
 * Usage:
 *   <MethodTooltip method="schulze" />
 *   <MethodTooltip method="schulze">Schulze</MethodTooltip>
 */
const MethodTooltip: React.FC<Props> = ({ method, children }) => {
  const label = children ?? METHOD_LABELS[method] ?? method;
  const description = METHOD_DESCRIPTIONS[method];
  const pro = METHOD_PROS[method];
  const con = METHOD_CONS[method];

  // No tooltip data available — render plain text.
  if (!description) return <span>{label}</span>;

  const tooltip = (
    <Tooltip id={`tip-${method}`} style={{ maxWidth: 300 }}>
      <div className="text-start p-1" style={{ fontSize: '0.82rem' }}>
        <div className="fw-bold mb-1" style={{ fontSize: '0.9rem' }}>
          {METHOD_LABELS[method] ?? method}
        </div>
        <div className="mb-2" style={{ lineHeight: 1.45, color: '#dee2e6' }}>
          {description}
        </div>
        {pro && (
          <div style={{ color: '#a8d5a2' }}>
            <span className="fw-semibold">✓ </span>{pro}
          </div>
        )}
        {con && (
          <div style={{ color: '#f5a5a5', marginTop: 3 }}>
            <span className="fw-semibold">✗ </span>{con}
          </div>
        )}
      </div>
    </Tooltip>
  );

  return (
    <OverlayTrigger
      trigger={['hover', 'focus']}
      placement="top"
      overlay={tooltip}
      delay={{ show: 250, hide: 100 }}
    >
      {/* tabIndex and role make it keyboard-reachable */}
      <span
        tabIndex={0}
        role="button"
        aria-label={`Définition : ${METHOD_LABELS[method] ?? method}`}
        style={{
          cursor: 'help',
          borderBottom: '1px dashed #adb5bd',
          display: 'inline',
          outline: 'none',
        }}
        onFocus={(e) => (e.currentTarget.style.borderBottomColor = '#0d6efd')}
        onBlur={(e) => (e.currentTarget.style.borderBottomColor = '#adb5bd')}
      >
        {label}
      </span>
    </OverlayTrigger>
  );
};

export default MethodTooltip;
