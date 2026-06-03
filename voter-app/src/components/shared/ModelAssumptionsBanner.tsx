/**
 * ModelAssumptionsBanner — collapsible permanent reminder of model limitations.
 * Shown on ElectionLabPage and any simulation-heavy view.
 *
 * Tailwind-migrated (Phase 6): the react-bootstrap <Collapse> is replaced by an
 * always-rendered detail div toggled with `hidden`, so the `banner-detail`
 * testid stays in the DOM (matching the old collapse behaviour).
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

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
      data-style="tailwind"
      className="mb-3 rounded-md border border-[#ffc107] bg-[#fff3cd] text-[0.75rem]"
    >
      {/* ── Always-visible header ── */}
      <div
        role="button"
        className="flex cursor-pointer select-none items-center gap-2 px-3 py-1.5"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        data-testid="banner-toggle"
      >
        <span>⚠️</span>
        <span className="font-semibold">{t('assumptions.bannerTitle')}</span>
        <span className="ml-auto text-[0.7rem] text-muted-foreground">
          {open ? '▲' : '▼'} {t('assumptions.bannerToggle')}
        </span>
      </div>

      {/* ── Collapsible detail ── */}
      <div data-testid="banner-detail" className={cn('px-3 pb-2.5 pt-1', !open && 'hidden')}>
        <div className="mb-2 flex flex-wrap gap-2">
          {ASSUMPTIONS.map((a) => (
            <span
              key={a}
              className="inline-flex items-center rounded-md bg-[#ffc107] px-2 py-0.5 text-[0.65rem] text-[#333]"
            >
              {t(`assumptions.short_${a}`)}
            </span>
          ))}
        </div>
        <div className="text-[0.72rem] leading-normal text-muted-foreground">
          {t('assumptions.bannerDesc')}
        </div>
        <Link to="/theory" className="text-[0.72rem]">
          {t('assumptions.bannerLink')} →
        </Link>
      </div>
    </div>
  );
};

export default ModelAssumptionsBanner;
