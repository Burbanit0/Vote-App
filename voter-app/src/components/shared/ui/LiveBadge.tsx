import React from 'react';
import { useTranslation } from 'react-i18next';

// Scoped keyframe injected once — avoids a CSS file dependency.
const STYLE = `
@keyframes _vl-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.15; }
}
._vl-live-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #0d6efd;
  animation: _vl-pulse 1.2s ease-in-out infinite;
  vertical-align: middle;
  margin-right: 5px;
  flex-shrink: 0;
}
`;

let _styleInjected = false;
function injectStyle() {
  if (_styleInjected || typeof document === 'undefined') return;
  const el = document.createElement('style');
  el.textContent = STYLE;
  document.head.appendChild(el);
  _styleInjected = true;
}

interface Props {
  loading: boolean;
  className?: string;
}

const LiveBadge: React.FC<Props> = ({ loading, className }) => {
  const { t } = useTranslation();

  if (!loading) return null;

  injectStyle();

  return (
    <span
      role="status"
      aria-label={t('simulation.recalculating')}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        fontSize: '0.75rem',
        color: '#6c757d',
        userSelect: 'none',
      }}
    >
      <span className="_vl-live-dot" aria-hidden="true" />
      {t('simulation.recalculating')}
    </span>
  );
};

export default LiveBadge;
