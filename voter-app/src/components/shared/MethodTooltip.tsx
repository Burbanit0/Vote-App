import React, { useRef, useState } from 'react';
import { useMethodCons, useMethodLabels, useMethodPros } from '../Simulation/simulationConstants';
import { METHOD_DESCRIPTIONS } from '../Simulation/simulationConstants';

interface Props {
  method: string;
  children?: React.ReactNode;
}

/**
 * Wraps a method name in an accessible tooltip. Tailwind-migrated (Phase 6):
 * the react-bootstrap Overlay/Tooltip is replaced by an absolutely-positioned
 * tooltip div above the trigger.
 *
 * Keyboard behaviour (WCAG 2.1 SC 2.1.1):
 *   - Tab        → focuses the trigger
 *   - Enter / Space → toggles the tooltip
 *   - Escape     → closes the tooltip and returns focus
 */
const MethodTooltip: React.FC<Props> = ({ method, children }) => {
  const methodLabels = useMethodLabels();
  const methodPros = useMethodPros();
  const methodCons = useMethodCons();

  const label = children ?? methodLabels[method] ?? method;
  const description = METHOD_DESCRIPTIONS[method];
  const pro = methodPros[method];
  const con = methodCons[method];

  const [show, setShow] = useState(false);
  const triggerRef = useRef<HTMLSpanElement>(null);

  if (!description) return <span>{label}</span>;

  const open = () => setShow(true);
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

  return (
    <span className="relative inline-block" data-style="tailwind">
      <span
        ref={triggerRef}
        tabIndex={0}
        role="button"
        aria-label={`${methodLabels[method] ?? method} — definition`}
        aria-expanded={show}
        aria-haspopup="true"
        className="inline cursor-help border-b border-dashed border-[#adb5bd] outline-none"
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        onKeyDown={handleKeyDown}
        onClick={() => setShow((prev) => !prev)}
      >
        {label}
      </span>

      {show && (
        <span
          role="tooltip"
          id={`tip-${method}`}
          className="absolute bottom-full left-1/2 z-50 mb-1 block w-[300px] max-w-[300px] -translate-x-1/2 rounded-md bg-slate-900 p-2 text-left text-[0.82rem] text-white shadow-lg"
        >
          <span className="mb-1 block text-[0.9rem] font-bold">
            {methodLabels[method] ?? method}
          </span>
          <span className="mb-2 block leading-snug text-slate-200">{description}</span>
          {pro && (
            <span className="block text-[#a8d5a2]">
              <span className="font-semibold" aria-hidden="true">
                ✓{' '}
              </span>
              {pro}
            </span>
          )}
          {con && (
            <span className="mt-[3px] block text-[#f5a5a5]">
              <span className="font-semibold" aria-hidden="true">
                ✗{' '}
              </span>
              {con}
            </span>
          )}
        </span>
      )}
    </span>
  );
};

export default MethodTooltip;
