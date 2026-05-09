import React from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../context/AuthContext';
import { Badge, Button, Container, Nav, Navbar as BootstrapNavbar, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { useTheme } from '../context/ThemeContext';
import { useExpertMode } from '../context/ExpertModeContext';

const NAV_LINKS = [
  { href: '/scenario-builder',      label: 'Simulateur' },
  { href: '/simulation/compare',    label: 'Méthodes' },
  { href: '/constitutional-crisis', label: 'Vote Blanc' },
];

const Navbar: React.FC = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { expertMode, setExpertMode } = useExpertMode();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) return null;

  return (
    <BootstrapNavbar
      data-tour="navbar"
      bg="white"
      expand="lg"
      className="border-bottom shadow-sm"
      sticky="top"
    >
      <Container>
        {/* Brand */}
        <BootstrapNavbar.Brand href="/" className="d-flex align-items-center gap-2 fw-bold" style={{ fontSize: '1.15rem' }}>
          <span style={{ fontSize: '1.3rem' }}>🗳️</span>
          Vote Lab
          <Badge bg="info" text="dark" style={{ fontSize: '0.6rem', fontWeight: 600, verticalAlign: 'middle', padding: '2px 6px' }}>
            Bêta
          </Badge>
        </BootstrapNavbar.Brand>

        <BootstrapNavbar.Toggle aria-controls="votelab-nav" />

        <BootstrapNavbar.Collapse id="votelab-nav">
          {/* Main nav */}
          <Nav className="me-auto">
            {NAV_LINKS.map(({ href, label }) => (
              <Nav.Link
                key={href}
                href={href}
                style={{ fontWeight: 500 }}
                active={typeof window !== 'undefined' && window.location.pathname === href}
              >
                {label}
              </Nav.Link>
            ))}
          </Nav>

          {/* Right side */}
          <Nav className="align-items-lg-center gap-2">
            {/* Expert / Débutant toggle */}
            <OverlayTrigger
              trigger={['hover', 'focus']}
              placement="bottom"
              overlay={
                <Tooltip id="tip-expert">
                  {expertMode
                    ? 'Passer en mode débutant (5 onglets, 5 méthodes)'
                    : 'Passer en mode expert (10 onglets, 15 méthodes)'}
                </Tooltip>
              }
            >
              <Button
                variant={expertMode ? 'primary' : 'outline-secondary'}
                size="sm"
                onClick={() => setExpertMode(!expertMode)}
                aria-label={expertMode ? 'Mode expert actif' : 'Mode débutant actif'}
                style={{ fontSize: '0.75rem', padding: '3px 10px', fontWeight: 600 }}
              >
                {expertMode ? 'Expert' : 'Débutant'}
              </Button>
            </OverlayTrigger>

            {/* Dark mode toggle */}
            <OverlayTrigger
              trigger={['hover', 'focus']}
              placement="bottom"
              overlay={<Tooltip id="tip-theme">{theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}</Tooltip>}
            >
              <Button
                variant="link"
                size="sm"
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}
                style={{ fontSize: '1.1rem', padding: '2px 6px', color: 'inherit', textDecoration: 'none' }}
              >
                {theme === 'dark' ? '☀️' : '🌙'}
              </Button>
            </OverlayTrigger>

            {/* Tour help button */}
            <OverlayTrigger
              trigger={['hover', 'focus']}
              placement="bottom"
              overlay={<Tooltip id="tip-tour">Lancer le tour guidé</Tooltip>}
            >
              <Nav.Link
                href="/?tour=1"
                className="d-flex align-items-center justify-content-center"
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: '50%',
                  border: '1.5px solid #6c757d',
                  color: '#6c757d',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  lineHeight: 1,
                  padding: 0,
                  flexShrink: 0,
                }}
                aria-label="Tour guidé"
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
                  Déconnexion
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline-primary" size="sm" onClick={() => navigate('/login')}>
                  Connexion
                </Button>
                <Button variant="primary" size="sm" onClick={() => navigate('/register')}>
                  Créer un compte
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
