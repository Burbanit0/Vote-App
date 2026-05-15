import React from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../context/AuthContext';
import { Badge, Button, Container, Nav, Navbar as BootstrapNavbar, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { useTheme } from '../context/ThemeContext';
import { useExpertMode } from '../context/ExpertModeContext';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';

const NAV_LINKS = [
  { href: '/scenario-builder',      key: 'nav.simulator' },
  { href: '/simulation/compare',    key: 'nav.methods' },
  { href: '/constitutional-crisis', key: 'nav.blankVote' },
  { href: '/quiz',                  key: 'nav.quiz' },
];

const Navbar: React.FC = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();
  const { t } = useTranslation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleLang = () => {
    i18n.changeLanguage(i18n.language === 'fr' ? 'en' : 'fr');
  };

  if (loading) return null;

  return (
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
  );
};

export default Navbar;
