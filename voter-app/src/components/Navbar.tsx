import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Dropdown } from '@/components/ui/dropdown';
import { Check } from '@/components/ui/form-controls';
import { Navbar as BootstrapNavbar, Nav } from '@/components/ui/navbar';
import { Container } from '@/components/ui/grid';
import { useTheme } from '../stores/useUIStore';
import { useExpertMode } from '../stores/useUIStore';
import { useTranslation } from 'react-i18next';
import i18n, { switchLanguage } from '../i18n';

// ── Navigation ────────────────────────────────────────────────────────────────
// Two destinations only: Playground (do) → Laboratoire (go deeper). Everything
// theory/mechanism/system lives inside the Laboratoire's anchors now.

// ── Settings row (used inside user dropdown) ──────────────────────────────────

const SettingRow: React.FC<{
  icon: string;
  label: string;
  checked: boolean;
  onToggle: () => void;
  badge?: string;
}> = ({ icon, label, checked, onToggle, badge }) => (
  <div
    role="button"
    tabIndex={0}
    className="dropdown-item flex items-center justify-between px-3 py-2"
    style={{ cursor: 'pointer', userSelect: 'none', fontSize: '0.85rem' }}
    onClick={(e) => {
      e.stopPropagation();
      onToggle();
    }}
    onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onToggle();
      }
    }}
  >
    <span className="flex items-center gap-2">
      <span>{icon}</span>
      <span>{label}</span>
      {badge && (
        <Badge variant="primary" style={{ fontSize: '0.6rem' }}>
          {badge}
        </Badge>
      )}
    </span>
    <Check
      type="switch"
      checked={checked}
      onChange={onToggle}
      onClick={(e) => e.stopPropagation()}
      style={{ pointerEvents: 'none' }}
    />
  </div>
);

// ── Main Navbar ───────────────────────────────────────────────────────────────

const Navbar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();
  const { t } = useTranslation();
  const [navExpanded, setNavExpanded] = useState(false);

  const toggleLang = () => switchLanguage(i18n.language === 'fr' ? 'en' : 'fr');
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '';

  return (
    <BootstrapNavbar
      data-tour="navbar"
      expand="lg"
      expanded={navExpanded}
      onToggle={setNavExpanded}
      className="border-b border-border shadow-sm"
      sticky="top"
      style={{ backgroundColor: 'var(--bs-body-bg)', borderColor: 'var(--bs-border-color)' }}
    >
      <Container className="flex flex-wrap items-center justify-between">
        {/* ── Brand ── */}
        <BootstrapNavbar.Brand
          href="/"
          className="font-display flex items-center gap-2 font-bold tracking-tight me-4"
          style={{ fontSize: '1.1rem' }}
          onClick={() => setNavExpanded(false)}
        >
          <span style={{ fontSize: '1.2rem' }}>🗳️</span>
          Vote Lab
          <Badge
            variant="info"
            style={{ fontSize: '0.58rem', fontWeight: 600, padding: '2px 5px' }}
          >
            Bêta
          </Badge>
        </BootstrapNavbar.Brand>

        <BootstrapNavbar.Toggle aria-controls="votelab-nav" aria-expanded={navExpanded} />

        <BootstrapNavbar.Collapse id="votelab-nav">
          {/* ── Main nav — two destinations: Playground → Laboratoire ── */}
          <Nav className="mr-auto lg:items-center gap-1">
            {/* Playground — hero link */}
            <Nav.Link
              href="/playground"
              className="font-semibold px-3 py-1 rounded"
              active={currentPath === '/playground'}
              onClick={() => setNavExpanded(false)}
              style={{
                background: currentPath === '/playground' ? 'var(--bs-primary)' : 'transparent',
                color: currentPath === '/playground' ? '#fff' : 'var(--bs-primary)',
                border: '1.5px solid var(--bs-primary)',
                fontSize: '0.88rem',
                transition: 'all 0.15s',
              }}
            >
              🎛 {t('nav.playground')}
            </Nav.Link>

            {/* Laboratoire — the "go deeper" destination */}
            <Nav.Link
              href="/laboratoire"
              className="font-semibold px-3 py-1 rounded"
              active={currentPath === '/laboratoire'}
              onClick={() => setNavExpanded(false)}
              style={{
                color: currentPath === '/laboratoire' ? 'var(--bs-primary)' : 'inherit',
                fontSize: '0.88rem',
                transition: 'all 0.15s',
              }}
            >
              🔬 {t('nav.laboratoire')}
            </Nav.Link>
          </Nav>

          {/* ── Right side ── */}
          <Nav className="lg:items-center gap-2">
            {/* Tour ? */}
            <Nav.Link
              href="/?tour=1"
              className="flex items-center justify-center"
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                border: '1.5px solid var(--bs-secondary-color, #6c757d)',
                color: 'var(--bs-secondary-color, #6c757d)',
                fontWeight: 700,
                fontSize: '0.8rem',
                padding: 0,
                flexShrink: 0,
              }}
              aria-label={t('nav.tourLabel')}
            >
              ?
            </Nav.Link>

            {/* ── User / Settings dropdown ── */}
            <Dropdown align="end">
              <Dropdown.Toggle
                variant="outline-secondary"
                size="sm"
                caret={false}
                className="flex items-center gap-2"
                style={{ border: '1px solid var(--bs-border-color)' }}
                id="user-settings-dropdown"
              >
                <span style={{ fontSize: '0.82rem' }}>⚙ {t('nav.settings')}</span>
              </Dropdown.Toggle>

              <Dropdown.Menu style={{ minWidth: 240 }}>
                {/* ── Settings section ── */}
                <div className="px-1 pb-1">
                  <div
                    className="text-muted-foreground px-2 py-1"
                    style={{
                      fontSize: '0.72rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                    }}
                  >
                    {t('nav.preferences')}
                  </div>

                  <SettingRow
                    icon={theme === 'dark' ? '☀️' : '🌙'}
                    label={theme === 'dark' ? t('nav.lightModeTip') : t('nav.darkModeTip')}
                    checked={theme === 'dark'}
                    onToggle={toggleTheme}
                  />

                  <SettingRow
                    icon="🌐"
                    label={i18n.language === 'fr' ? 'Switch to English' : 'Passer en français'}
                    checked={i18n.language !== 'fr'}
                    onToggle={toggleLang}
                  />

                  <SettingRow
                    icon="⚡"
                    label={expertMode ? t('nav.expert') : t('nav.beginner')}
                    checked={expertMode}
                    onToggle={() => setExpertMode(!expertMode)}
                  />
                </div>

                <hr className="my-1" style={{ borderColor: 'var(--bs-border-color)' }} />

                <a
                  href="https://github.com/Burbanit0/Vote-App/issues/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="dropdown-item flex items-center gap-2 px-3 py-2"
                  style={{ fontSize: '0.85rem', textDecoration: 'none' }}
                >
                  🐛 {t('nav.reportBug')}
                </a>
              </Dropdown.Menu>
            </Dropdown>
          </Nav>
        </BootstrapNavbar.Collapse>
      </Container>
    </BootstrapNavbar>
  );
};

export default Navbar;
