import React, { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../context/AuthContext';
import {
  Badge, Button, Container, Form, Modal, Nav, Navbar as BootstrapNavbar,
  OverlayTrigger, Tooltip,
} from 'react-bootstrap';
import { useTheme } from '../context/ThemeContext';
import { useExpertMode } from '../context/ExpertModeContext';
import { useTeacherMode } from '../context/TeacherModeContext';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';

const NAV_LINKS = [
  { href: '/scenario-builder',      key: 'nav.simulator' },
  { href: '/simulation/compare',    key: 'nav.methods' },
  { href: '/constitutional-crisis', key: 'nav.blankVote' },
  { href: '/quiz',                  key: 'nav.quiz' },
  { href: '/what-if',              key: 'nav.whatIf' },
  { href: '/campaign',             key: 'nav.campaign' },
  { href: '/blank-contagion',      key: 'nav.blankContagion' },
];

const LS_PASS = 'votelab_teacher_pass';

const Navbar: React.FC = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();
  const { teacherMode, setTeacherMode, slides } = useTeacherMode();
  const { t } = useTranslation();

  // ── Teacher mode password modal ──────────────────────────────────────────
  const [showPassModal, setShowPassModal]   = useState(false);
  const [passInput,     setPassInput]       = useState('');
  const [passConfirm,   setPassConfirm]     = useState('');
  const [passError,     setPassError]       = useState('');
  const passInputRef                        = useRef<HTMLInputElement>(null);

  const storedPass = useCallback(
    () => localStorage.getItem(LS_PASS),
    [],
  );

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
      // First time — set a new password
      if (passInput.length < 4) { setPassError('Mot de passe trop court (min. 4 caractères).'); return; }
      if (passInput !== passConfirm) { setPassError('Les mots de passe ne correspondent pas.'); return; }
      localStorage.setItem(LS_PASS, passInput);
      setTeacherMode(true);
      setShowPassModal(false);
    } else {
      // Check existing password
      if (passInput !== saved) { setPassError('Mot de passe incorrect.'); return; }
      setTeacherMode(true);
      setShowPassModal(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleLang = () => {
    i18n.changeLanguage(i18n.language === 'fr' ? 'en' : 'fr');
  };

  if (loading) return null;

  const isPasswordSet = !!storedPass();

  return (
    <>
      <BootstrapNavbar
        data-tour="navbar"
        expand="lg"
        className="border-bottom shadow-sm"
        sticky="top"
        style={{ backgroundColor: 'var(--bs-body-bg)', borderColor: 'var(--bs-border-color)' }}
      >
        <Container>
          <BootstrapNavbar.Brand href="/" className="d-flex align-items-center gap-2 fw-bold" style={{ fontSize: '1.15rem' }}>
            <span style={{ fontSize: '1.3rem' }}>🗳️</span>
            Vote Lab
            <Badge bg="info" text="dark" style={{ fontSize: '0.6rem', fontWeight: 600, verticalAlign: 'middle', padding: '2px 6px' }}>
              Bêta
            </Badge>
          </BootstrapNavbar.Brand>

          <BootstrapNavbar.Toggle aria-controls="votelab-nav" />

          <BootstrapNavbar.Collapse id="votelab-nav">
            <Nav className="me-auto">
              {NAV_LINKS.map(({ href, key }) => (
                <Nav.Link
                  key={href}
                  href={href}
                  style={{ fontWeight: 500 }}
                  active={typeof window !== 'undefined' && window.location.pathname === href}
                >
                  {t(key)}
                </Nav.Link>
              ))}
            </Nav>

            <Nav className="align-items-lg-center gap-2">
              {/* Expert / Beginner toggle */}
              <OverlayTrigger
                trigger={['hover', 'focus']}
                placement="bottom"
                overlay={
                  <Tooltip id="tip-expert">
                    {expertMode ? t('nav.expertTip') : t('nav.beginnerTip')}
                  </Tooltip>
                }
              >
                <Button
                  variant={expertMode ? 'primary' : 'outline-secondary'}
                  size="sm"
                  onClick={() => setExpertMode(!expertMode)}
                  aria-label={expertMode ? t('nav.expert') : t('nav.beginner')}
                  style={{ fontSize: '0.75rem', padding: '3px 10px', fontWeight: 600 }}
                >
                  {expertMode ? t('nav.expert') : t('nav.beginner')}
                </Button>
              </OverlayTrigger>

              {/* Teacher Mode toggle */}
              <OverlayTrigger
                trigger={['hover', 'focus']}
                placement="bottom"
                overlay={
                  <Tooltip id="tip-teacher">
                    {teacherMode
                      ? `Mode Enseignant actif — ${slides.length} slide${slides.length !== 1 ? 's' : ''} (cliquer pour désactiver)`
                      : 'Activer le Mode Enseignant'}
                  </Tooltip>
                }
              >
                <Button
                  variant={teacherMode ? 'success' : 'outline-secondary'}
                  size="sm"
                  onClick={handleTeacherClick}
                  aria-label={teacherMode ? 'Désactiver le mode enseignant' : 'Activer le mode enseignant'}
                  style={{ fontSize: '0.8rem', padding: '3px 10px', fontWeight: 600 }}
                >
                  🎓{teacherMode ? ` ${slides.length}` : ''}
                </Button>
              </OverlayTrigger>

              {/* Language toggle */}
              <OverlayTrigger
                trigger={['hover', 'focus']}
                placement="bottom"
                overlay={<Tooltip id="tip-lang">{i18n.language === 'fr' ? 'Switch to English' : 'Passer en français'}</Tooltip>}
              >
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={toggleLang}
                  aria-label={i18n.language === 'fr' ? 'Switch to English' : 'Passer en français'}
                  style={{ fontSize: '0.75rem', padding: '3px 10px', fontWeight: 700, minWidth: 42 }}
                >
                  {i18n.language === 'fr' ? 'FR' : 'EN'}
                </Button>
              </OverlayTrigger>

              {/* Dark mode toggle */}
              <OverlayTrigger
                trigger={['hover', 'focus']}
                placement="bottom"
                overlay={<Tooltip id="tip-theme">{theme === 'dark' ? t('nav.lightModeTip') : t('nav.darkModeTip')}</Tooltip>}
              >
                <Button
                  variant="link"
                  size="sm"
                  onClick={toggleTheme}
                  aria-label={theme === 'dark' ? t('nav.lightModeTip') : t('nav.darkModeTip')}
                  style={{ fontSize: '1.1rem', padding: '2px 6px', color: 'inherit', textDecoration: 'none' }}
                >
                  {theme === 'dark' ? '☀️' : '🌙'}
                </Button>
              </OverlayTrigger>

              {/* Tour help button */}
              <OverlayTrigger
                trigger={['hover', 'focus']}
                placement="bottom"
                overlay={<Tooltip id="tip-tour">{t('nav.guidedTour')}</Tooltip>}
              >
                <Nav.Link
                  href="/?tour=1"
                  className="d-flex align-items-center justify-content-center"
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: '50%',
                    border: '1.5px solid var(--bs-secondary-color, #6c757d)',
                    color: 'var(--bs-secondary-color, #6c757d)',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    lineHeight: 1,
                    padding: 0,
                    flexShrink: 0,
                  }}
                  aria-label={t('nav.tourLabel')}
                >
                  ?
                </Nav.Link>
              </OverlayTrigger>

              {user ? (
                <>
                  <Nav.Link href="/profile" className="text-muted small">
                    👤 {user.username}
                  </Nav.Link>
                  <Button variant="outline-secondary" size="sm" onClick={handleLogout}>
                    {t('nav.logout')}
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="outline-primary" size="sm" onClick={() => navigate('/login')}>
                    {t('nav.login')}
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => navigate('/register')}>
                    {t('nav.register')}
                  </Button>
                </>
              )}
            </Nav>
          </BootstrapNavbar.Collapse>
        </Container>
      </BootstrapNavbar>

      {/* ── Teacher mode password modal ─────────────────────────────────────── */}
      <Modal show={showPassModal} onHide={() => setShowPassModal(false)} centered size="sm">
        <Modal.Header closeButton>
          <Modal.Title style={{ fontSize: '1rem' }}>
            🎓 {isPasswordSet ? 'Mode Enseignant' : 'Créer un accès enseignant'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {!isPasswordSet && (
            <p className="text-muted small mb-3">
              Définissez un mot de passe pour protéger le Mode Enseignant. Il sera stocké
              localement dans ce navigateur.
            </p>
          )}
          <Form
            onSubmit={(e) => { e.preventDefault(); handlePassSubmit(); }}
          >
            <Form.Group className="mb-2">
              <Form.Label className="small">
                {isPasswordSet ? 'Mot de passe' : 'Nouveau mot de passe'}
              </Form.Label>
              <Form.Control
                ref={passInputRef}
                type="password"
                size="sm"
                value={passInput}
                onChange={(e) => { setPassInput(e.target.value); setPassError(''); }}
                placeholder={isPasswordSet ? '••••••' : 'Min. 4 caractères'}
                autoComplete="current-password"
              />
            </Form.Group>
            {!isPasswordSet && (
              <Form.Group className="mb-2">
                <Form.Label className="small">Confirmer le mot de passe</Form.Label>
                <Form.Control
                  type="password"
                  size="sm"
                  value={passConfirm}
                  onChange={(e) => { setPassConfirm(e.target.value); setPassError(''); }}
                  placeholder="Répéter le mot de passe"
                  autoComplete="new-password"
                />
              </Form.Group>
            )}
            {passError && (
              <div className="text-danger small mb-2">{passError}</div>
            )}
            <Button type="submit" variant="success" size="sm" className="w-100">
              {isPasswordSet ? 'Activer le mode enseignant' : 'Créer et activer'}
            </Button>
          </Form>
          {isPasswordSet && (
            <div className="mt-2 text-center">
              <button
                className="btn btn-link btn-sm text-muted"
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
