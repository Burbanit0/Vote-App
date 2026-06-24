import React, { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../stores/useAuthStore';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dropdown, NavDropdown } from '@/components/ui/dropdown';
import { Modal } from '@/components/ui/modal';
import { Control, Check } from '@/components/ui/form-controls';
import { Navbar as BootstrapNavbar, Nav } from '@/components/ui/navbar';
import { Container } from '@/components/ui/grid';
import { useTheme } from '../stores/useUIStore';
import { useExpertMode } from '../stores/useUIStore';
import { useTeacherMode } from '../stores/useUIStore';
import { useTranslation } from 'react-i18next';
import i18n, { switchLanguage } from '../i18n';

// ── Navigation groups ─────────────────────────────────────────────────────────

const NAV_LEARN = [
  { href: '/quiz', icon: '📝', key: 'nav.quiz' },
  { href: '/regimes-internationaux', icon: '🌍', key: 'nav.regimesInternationaux' },
];

const NAV_EXPLORE = [
  { href: '/what-if', icon: '🔮', key: 'nav.whatIf' },
  { href: '/quadratic-funding', icon: '💰', key: 'nav.quadraticFunding' },
  { href: '/tech-democracy', icon: '💻', key: 'nav.techDemocracy' },
  { href: '/theory', icon: '🏛', key: 'nav.theory' },
  { href: '/galerie', icon: '🗃️', key: 'nav.gallery' },
  { href: '/api-docs', icon: '🔌', key: 'nav.apiDocs' },
];

const LS_PASS = 'votelab_teacher_pass';

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
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();
  const { teacherMode, setTeacherMode, slides } = useTeacherMode();
  const { t } = useTranslation();
  const [navExpanded, setNavExpanded] = useState(false);

  // ── Teacher mode password modal ──────────────────────────────────────────
  const [showPassModal, setShowPassModal] = useState(false);
  const [passInput, setPassInput] = useState('');
  const [passConfirm, setPassConfirm] = useState('');
  const [passError, setPassError] = useState('');
  const passInputRef = useRef<HTMLInputElement>(null);

  const storedPass = useCallback(() => localStorage.getItem(LS_PASS), []);

  const handleTeacherClick = () => {
    if (teacherMode) {
      setTeacherMode(false);
      return;
    }
    setPassInput('');
    setPassConfirm('');
    setPassError('');
    setShowPassModal(true);
    setTimeout(() => passInputRef.current?.focus(), 80);
  };

  const handlePassSubmit = () => {
    const saved = storedPass();
    if (!saved) {
      if (passInput.length < 4) {
        setPassError('Mot de passe trop court (min. 4 caractères).');
        return;
      }
      if (passInput !== passConfirm) {
        setPassError('Les mots de passe ne correspondent pas.');
        return;
      }
      localStorage.setItem(LS_PASS, passInput);
      setTeacherMode(true);
      setShowPassModal(false);
    } else {
      if (passInput !== saved) {
        setPassError('Mot de passe incorrect.');
        return;
      }
      setTeacherMode(true);
      setShowPassModal(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  const toggleLang = () => switchLanguage(i18n.language === 'fr' ? 'en' : 'fr');
  const isPasswordSet = !!storedPass();
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '';

  if (loading) return null;

  return (
    <>
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
            {/* ── Main nav ── */}
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

              {/* Campagne & dynamique — page 2 of the journey (temporal) */}
              <Nav.Link
                href="/campagne"
                className="font-semibold px-3 py-1 rounded"
                active={currentPath === '/campagne'}
                onClick={() => setNavExpanded(false)}
                style={{
                  background: currentPath === '/campagne' ? 'var(--bs-primary)' : 'transparent',
                  color: currentPath === '/campagne' ? '#fff' : 'var(--bs-primary)',
                  border: '1.5px solid var(--bs-primary)',
                  fontSize: '0.88rem',
                  transition: 'all 0.15s',
                }}
              >
                📈 {t('nav.campaign')}
              </Nav.Link>

              {/* Apprendre dropdown */}
              <NavDropdown title={t('nav.learn')} id="nav-learn" renderMenuOnMount>
                {NAV_LEARN.map(({ href, icon, key }) => (
                  <NavDropdown.Item key={href} href={href}>
                    <span className="me-2">{icon}</span>
                    {t(key)}
                  </NavDropdown.Item>
                ))}
                <NavDropdown.Divider />
                <NavDropdown.Item href="/?tour=1">
                  <span className="me-2">🎓</span>
                  {t('nav.guidedTour')}
                </NavDropdown.Item>
              </NavDropdown>

              {/* Explorer dropdown */}
              <NavDropdown title={t('nav.explore')} id="nav-explore" renderMenuOnMount>
                {NAV_EXPLORE.map(({ href, icon, key }) => (
                  <NavDropdown.Item key={href} href={href}>
                    <span className="me-2">{icon}</span>
                    {t(key)}
                  </NavDropdown.Item>
                ))}
              </NavDropdown>
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
                  {user ? (
                    <>
                      <span>👤</span>
                      <span
                        style={{
                          maxWidth: 100,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: '0.82rem',
                        }}
                      >
                        {user.username}
                      </span>
                    </>
                  ) : (
                    <span style={{ fontSize: '0.82rem' }}>⚙ {t('nav.settings')}</span>
                  )}
                </Dropdown.Toggle>

                <Dropdown.Menu style={{ minWidth: 240 }}>
                  {/* Header when logged in */}
                  {user && (
                    <>
                      <Dropdown.Header>
                        <span className="font-semibold">{user.username}</span>
                        <div className="text-muted-foreground" style={{ fontSize: '0.75rem' }}>
                          {user.role}
                        </div>
                      </Dropdown.Header>
                      <Dropdown.Divider />
                    </>
                  )}

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

                    <SettingRow
                      icon="🎓"
                      label={teacherMode ? 'Mode enseignant actif' : 'Mode enseignant'}
                      checked={teacherMode}
                      onToggle={handleTeacherClick}
                      badge={teacherMode && slides.length > 0 ? String(slides.length) : undefined}
                    />
                  </div>

                  <Dropdown.Divider />

                  {/* ── Auth section ── */}
                  {user ? (
                    <>
                      <Dropdown.Item href="/profile">
                        <span className="me-2">👤</span>
                        {t('nav.profile')}
                      </Dropdown.Item>
                      <Dropdown.Item onClick={handleLogout} className="text-[#dc3545]">
                        <span className="me-2">↩</span>
                        {t('nav.logout')}
                      </Dropdown.Item>
                    </>
                  ) : (
                    <div className="flex gap-2 px-3 py-2">
                      <Button
                        variant="outline-primary"
                        size="sm"
                        className="grow"
                        onClick={() => navigate('/login')}
                      >
                        {t('nav.login')}
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        className="grow"
                        onClick={() => navigate('/register')}
                      >
                        {t('nav.register')}
                      </Button>
                    </div>
                  )}
                </Dropdown.Menu>
              </Dropdown>
            </Nav>
          </BootstrapNavbar.Collapse>
        </Container>
      </BootstrapNavbar>

      {/* ── Teacher mode password modal ───────────────────────────────────── */}
      <Modal show={showPassModal} onHide={() => setShowPassModal(false)} centered size="sm">
        <Modal.Header closeButton>
          <Modal.Title style={{ fontSize: '1rem' }}>
            🎓 {isPasswordSet ? 'Mode Enseignant' : 'Créer un accès enseignant'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {!isPasswordSet && (
            <p className="text-muted-foreground text-sm mb-3">
              Définissez un mot de passe pour protéger le Mode Enseignant.
            </p>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handlePassSubmit();
            }}
          >
            <div className="mb-2">
              <label className="text-sm mb-1 inline-block">
                {isPasswordSet ? 'Mot de passe' : 'Nouveau mot de passe'}
              </label>
              <Control
                ref={passInputRef}
                type="password"
                size="sm"
                value={passInput}
                onChange={(e) => {
                  setPassInput(e.target.value);
                  setPassError('');
                }}
                placeholder={isPasswordSet ? '••••••' : 'Min. 4 caractères'}
                autoComplete="current-password"
              />
            </div>
            {!isPasswordSet && (
              <div className="mb-2">
                <label className="text-sm mb-1 inline-block" htmlFor="pass-confirm">
                  Confirmer
                </label>
                <Control
                  id="pass-confirm"
                  type="password"
                  size="sm"
                  value={passConfirm}
                  onChange={(e) => {
                    setPassConfirm(e.target.value);
                    setPassError('');
                  }}
                  placeholder="Répéter le mot de passe"
                  autoComplete="new-password"
                />
              </div>
            )}
            {passError && <div className="text-[#dc3545] text-sm mb-2">{passError}</div>}
            <Button type="submit" variant="success" size="sm" className="w-full">
              {isPasswordSet ? 'Activer' : 'Créer et activer'}
            </Button>
          </form>
          {isPasswordSet && (
            <div className="mt-2 text-center">
              <button
                className="btn btn-link btn-sm text-muted-foreground"
                style={{ fontSize: '0.75rem' }}
                onClick={() => {
                  if (window.confirm('Réinitialiser le mot de passe enseignant ?')) {
                    localStorage.removeItem(LS_PASS);
                    setShowPassModal(false);
                    setTimeout(() => handleTeacherClick(), 100);
                  }
                }}
                type="button"
              >
                Réinitialiser le mot de passe
              </button>
            </div>
          )}
        </Modal.Body>
      </Modal>
    </>
  );
};

export default Navbar;
