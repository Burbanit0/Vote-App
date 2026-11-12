import React, { useState } from 'react';
import {
  Bug,
  FlaskConical,
  GraduationCap,
  Moon,
  Settings,
  SlidersHorizontal,
  Sun,
  Type,
  Vote,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Dropdown } from '@/components/ui/dropdown';
import { Segmented } from '@/components/ui/segmented';
import { Switch } from '@/components/ui/switch';
import { Navbar as BootstrapNavbar, Nav } from '@/components/ui/navbar';
import { Container } from '@/components/ui/grid';
import { useTheme } from '../stores/useUIStore';
import { useExpertMode } from '../stores/useUIStore';
import { usePlainLanguage } from '../stores/useUIStore';
import { useTranslation } from 'react-i18next';
import i18n, { switchLanguage } from '../i18n';
import { NEW_ISSUE_URL } from '../lib/repo';

// ── Navigation ────────────────────────────────────────────────────────────────
// Three destinations: Playground (the instrument, hero) → Laboratoire (go deeper)
// → À vous de jouer (cast one ballot yourself). Everything theory/mechanism/system
// lives inside the Laboratoire's fiches. Polity (a research run explorer, not part
// of the teaching path) is linked from the home page footer; its route is unchanged.

// Line icons, one size and one stroke for the whole bar (they replaced emojis).
const ICON = { size: 16, strokeWidth: 1.75, 'aria-hidden': true } as const;

const LINKS = [
  { path: '/playground', testid: 'nav-playground', key: 'nav.playground', Icon: SlidersHorizontal },
  { path: '/laboratoire', testid: 'nav-laboratoire', key: 'nav.laboratoire', Icon: FlaskConical },
  { path: '/a-vous-de-jouer', testid: 'nav-a-vous-de-jouer', key: 'nav.play', Icon: Vote },
] as const;

/**
 * The page you are on is marked three ways: a tinted background, a petrol icon, and a
 * petrol bar on the bar's bottom edge (on the phone menu, along the item's left side).
 */
const LINK =
  'relative flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[0.88rem] font-semibold transition-colors hover:bg-muted';
const ACTIVE =
  'nav-active bg-primary/10 text-foreground max-lg:shadow-[inset_3px_0_0_var(--primary)] lg:after:absolute lg:after:inset-x-3 lg:after:-bottom-2 lg:after:h-[3px] lg:after:rounded-full lg:after:bg-primary';

/** One preference: its name above, its control below. */
const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex flex-col gap-1.5 px-2 py-1.5">
    <span className="text-[0.72rem] font-semibold text-muted-foreground">{label}</span>
    {children}
  </div>
);

// ── Main Navbar ───────────────────────────────────────────────────────────────

const Navbar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();
  const { plainLanguage, setPlainLanguage } = usePlainLanguage();
  const { t } = useTranslation();
  const [navExpanded, setNavExpanded] = useState(false);

  // The site may be served under a base path (GitHub Pages: /Vote-App/); these links load
  // a whole page, so they carry it, and the active link is read without it.
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const currentPath = window.location.pathname.slice(base.length);

  return (
    <BootstrapNavbar
      data-testid="navbar"
      data-touch
      expand="lg"
      expanded={navExpanded}
      onToggle={setNavExpanded}
      // On a phone its items are 44 px (W3.6); a 1-px padding keeps the bar at 47 px, as
      // before, under the stories' sticky bar at 48 (top-12).
      className="border-b border-border shadow-sm max-sm:py-px"
      sticky="top"
      style={{ backgroundColor: 'var(--bs-body-bg)', borderColor: 'var(--bs-border-color)' }}
    >
      <Container className="flex flex-wrap items-center justify-between">
        {/* ── Brand ── */}
        <BootstrapNavbar.Brand
          href={`${base}/`}
          className="font-display flex items-center gap-2 font-extrabold me-4"
          style={{ fontSize: '1.45rem', lineHeight: 1 }}
          onClick={() => setNavExpanded(false)}
        >
          {/* The ballot slip, cast: a solid sheet with its corner folded back in petrol
              and one tick. Its outline is the shape the homepage entrance folds the
              screen into (data-brand-mark, slipPolygon in lib/home/motion.ts). */}
          <svg data-brand-mark width="20" height="26" viewBox="0 0 20 26" aria-hidden="true">
            <path d="M1 1h12l6 6v18H1z" fill="currentColor" />
            <path d="M13 1v6h6z" style={{ fill: 'var(--primary)' }} />
            <path
              d="M5.5 15.5l3 3 6-7"
              fill="none"
              style={{ stroke: 'var(--background)' }}
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Vote Lab
          <span className="rounded-full border border-border px-1.5 py-px font-sans text-[0.62rem] font-semibold tracking-normal text-muted-foreground">
            {t('nav.beta')}
          </span>
        </BootstrapNavbar.Brand>

        <BootstrapNavbar.Toggle
          aria-controls="votelab-nav"
          aria-expanded={navExpanded}
          aria-label={t('nav.toggleLabel')}
          data-testid="navbar-toggle"
        />

        <BootstrapNavbar.Collapse id="votelab-nav">
          {/* ── Main nav — Playground → Laboratoire → À vous de jouer ── */}
          <Nav className="mr-auto gap-1 lg:items-center">
            {LINKS.map(({ path, testid, key, Icon }) => {
              const on = currentPath === path;
              return (
                <Nav.Link
                  key={path}
                  href={`${base}${path}`}
                  data-testid={testid}
                  active={on}
                  onClick={() => setNavExpanded(false)}
                  className={cn(LINK, on && ACTIVE)}
                >
                  <Icon {...ICON} className={cn(on && 'text-primary')} />
                  {t(key)}
                </Nav.Link>
              );
            })}
          </Nav>

          {/* ── Right side ── */}
          {/* On a phone it lines up with the links; on a desktop it ends the bar, so its
              menu opens leftwards, inside the window. */}
          <Nav className="gap-2 max-lg:self-start lg:items-center">
            {/* ── User / Settings dropdown ── */}
            <Dropdown>
              <Dropdown.Toggle
                variant="outline-secondary"
                size="sm"
                className="flex items-center gap-2"
                style={{ border: '1px solid var(--bs-border-color)' }}
                id="user-settings-dropdown"
              >
                <Settings {...ICON} />
                <span style={{ fontSize: '0.82rem' }}>{t('nav.settings')}</span>
              </Dropdown.Toggle>

              <Dropdown.Menu className="lg:right-0 lg:left-auto" style={{ minWidth: 260 }}>
                <div className="flex flex-col gap-1 p-1">
                  <Field label={t('nav.theme')}>
                    <Segmented
                      label={t('nav.theme')}
                      value={theme === 'dark' ? 'dark' : 'light'}
                      onChange={toggleTheme}
                      options={[
                        { value: 'light', label: t('nav.light'), icon: Sun, testid: 'theme-light' },
                        { value: 'dark', label: t('nav.dark'), icon: Moon, testid: 'theme-dark' },
                      ]}
                    />
                  </Field>
                  <Field label={t('nav.language')}>
                    <Segmented
                      label={t('nav.language')}
                      value={i18n.language === 'fr' ? 'fr' : 'en'}
                      onChange={(lang) => void switchLanguage(lang)}
                      options={[
                        // Each language is named in itself, so it can be found from the other.
                        { value: 'fr', label: 'Français', testid: 'lang-fr' },
                        { value: 'en', label: 'English', testid: 'lang-en' },
                      ]}
                    />
                  </Field>
                  <Field label={t('nav.level')}>
                    <Segmented
                      label={t('nav.level')}
                      value={expertMode ? 'expert' : 'beginner'}
                      onChange={(level) => setExpertMode(level === 'expert')}
                      options={[
                        { value: 'beginner', label: t('nav.beginner'), testid: 'level-beginner' },
                        {
                          value: 'expert',
                          label: t('nav.expert'),
                          icon: GraduationCap,
                          testid: 'level-expert',
                        },
                      ]}
                    />
                  </Field>
                  <Switch
                    checked={plainLanguage}
                    onChange={setPlainLanguage}
                    testid="setting-plain"
                  >
                    <Type {...ICON} className="shrink-0 text-muted-foreground" />
                    {t('nav.plain')}
                  </Switch>
                </div>

                <hr className="my-1" style={{ borderColor: 'var(--bs-border-color)' }} />

                <a
                  href={NEW_ISSUE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="dropdown-item flex items-center gap-2 px-3 py-2"
                  style={{ fontSize: '0.85rem', textDecoration: 'none' }}
                >
                  <Bug {...ICON} className="shrink-0 text-muted-foreground" />
                  {t('nav.reportBug')}
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
