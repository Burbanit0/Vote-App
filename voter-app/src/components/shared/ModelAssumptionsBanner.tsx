/**
 * ModelAssumptionsBanner — collapsible permanent reminder of model limitations.
 * Shown on ElectionLabPage and any simulation-heavy view.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Collapse } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const ASSUMPTIONS = [
  'stable_preferences',
  'single_peaked',
  'rational_voters',
  'fixed_electorate',
  'measurable_utilities',
  'two_d_ideology',
] as const;

const ModelAssumptionsBanner: React.FC = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <div
      data-testid="assumptions-banner"
      style={{
        background: '#fff3cd',
        border: '1px solid #ffc107',
        borderRadius: 6,
        marginBottom: 12,
        fontSize: '0.75rem',
      }}
    >
      {/* ── Always-visible header ── */}
      <div
        role="button"
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px', cursor: 'pointer', userSelect: 'none',
        }}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        data-testid="banner-toggle"
      >
        <span>⚠️</span>
        <span className="fw-semibold">{t('assumptions.bannerTitle')}</span>
        <span className="text-muted ms-auto" style={{ fontSize: '0.7rem' }}>
          {open ? '▲' : '▼'} {t('assumptions.bannerToggle')}
        </span>
      </div>

      {/* ── Collapsible detail ── */}
      <Collapse in={open}>
        <div data-testid="banner-detail" style={{ padding: '4px 12px 10px' }}>
          <div className="d-flex flex-wrap gap-2 mb-2">
            {ASSUMPTIONS.map(a => (
              <span key={a}
                className="badge"
                style={{ background: '#ffc107', color: '#333', fontSize: '0.65rem' }}>
                {t(`assumptions.short_${a}`)}
              </span>
            ))}
          </div>
          <div className="text-muted" style={{ fontSize: '0.72rem', lineHeight: 1.5 }}>
            {t('assumptions.bannerDesc')}
          </div>
          <Link to="/theory" style={{ fontSize: '0.72rem' }}>
            {t('assumptions.bannerLink')} →
          </Link>
        </div>
      </Collapse>
    </div>
  );
};

export default ModelAssumptionsBanner;
