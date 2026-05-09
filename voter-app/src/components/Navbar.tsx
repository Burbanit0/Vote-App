import React from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../context/AuthContext';
import { Badge, Button, Container, Nav, Navbar as BootstrapNavbar } from 'react-bootstrap';

const NAV_LINKS = [
  { href: '/scenario-builder',     label: 'Simulateur' },
  { href: '/simulation/compare',   label: 'Méthodes' },
  { href: '/constitutional-crisis', label: 'Vote Blanc' },
];

const Navbar: React.FC = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) return null;

  return (
    <BootstrapNavbar bg="white" expand="lg" className="border-bottom shadow-sm" sticky="top">
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
