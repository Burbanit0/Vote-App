import React, { useCallback, useEffect, useState } from 'react';
import { Badge, Button, Card, Col, Container, Row, Spinner } from 'react-bootstrap';
import { runComparisonSimulation } from '../services/simulationCompareApi';
import OnboardingTour from '../components/shared/OnboardingTour';

// ── Election thumbnails ─────────────────────────────────────────────────────

const ELECTIONS = [
  {
    key: 'crisis_election',
    flag: '🚨',
    name: 'Élection de crise',
    year: 2027,
    country: 'France (fictif)',
    finding: 'Le vote blanc gagne — crise constitutionnelle simulée',
    badge: { text: 'Cas pédagogique', bg: 'danger' },
  },
  {
    key: 'france_2022',
    flag: '🇫🇷',
    name: 'Présidentielle',
    year: 2022,
    country: 'France',
    finding: '12 candidats, fragmentation extrême — qui aurait gagné sous Schulze ?',
    badge: null,
  },
  {
    key: 'france_2002',
    flag: '🇫🇷',
    name: 'Présidentielle',
    year: 2002,
    country: 'France',
    finding: "Jospin éliminé par Le Pen — 11 méthodes sur 15 l'auraient sauvé",
    badge: { text: 'Cas classique', bg: 'warning' },
  },
  {
    key: 'us_1992',
    flag: '🇺🇸',
    name: 'Présidentielle',
    year: 1992,
    country: 'États-Unis',
    finding: 'Perot : 18.9% des voix, gagnant potentiel de Condorcet éliminé',
    badge: null,
  },
];

// ── Dynamic stats hook ──────────────────────────────────────────────────────

interface QuickStats {
  disagreeingMethods: number | null;
  totalMethods: number;
  condorcetExists: boolean | null;
  loading: boolean;
}

function useQuickStats(): QuickStats {
  const [state, setState] = useState<QuickStats>({
    disagreeingMethods: null,
    totalMethods: 15,
    condorcetExists: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    runComparisonSimulation({ num_voters: 200, candidates: ['Alice', 'Bob', 'Charlie'] })
      .then((r) => {
        if (cancelled) return;
        const methods = Object.values(r.methods);
        const pluralityWinner = r.methods['plurality']?.winner;
        const disagreeing = methods.filter(
          (m) => m.winner !== null && m.winner !== pluralityWinner
        ).length;
        setState({
          disagreeingMethods: disagreeing,
          totalMethods: methods.length,
          condorcetExists: r.condorcet_winner !== null,
          loading: false,
        });
      })
      .catch(() => {
        if (!cancelled)
          setState({ disagreeingMethods: null, totalMethods: 15, condorcetExists: null, loading: false });
      });
    return () => { cancelled = true; };
  }, []);

  return state;
}

// ── Sub-components ──────────────────────────────────────────────────────────

const ActionCard: React.FC<{
  emoji: string;
  title: string;
  description: string;
  href: string;
  buttonText: string;
  variant?: string;
  highlight?: boolean;
}> = ({ emoji, title, description, href, buttonText, variant = 'primary', highlight }) => (
  <Card
    className="h-100 text-center"
    style={{
      border: highlight ? '2px solid #0d6efd' : undefined,
      transition: 'transform 0.15s, box-shadow 0.15s',
    }}
    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-3px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 6px 20px rgba(0,0,0,0.12)'; }}
    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = ''; (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
  >
    <Card.Body className="p-4 d-flex flex-column align-items-center">
      <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>{emoji}</div>
      <Card.Title className="fw-bold mb-2">{title}</Card.Title>
      <Card.Text className="text-muted small flex-grow-1">{description}</Card.Text>
      <a href={href}>
        <Button variant={variant} className="mt-3 px-4">{buttonText}</Button>
      </a>
    </Card.Body>
  </Card>
);

const StatCard: React.FC<{ value: React.ReactNode; label: string; sub?: string }> = ({ value, label, sub }) => (
  <div className="text-center px-3 py-4 rounded-3" style={{ backgroundColor: 'var(--bs-secondary-bg)' }}>
    <div style={{ fontSize: '2.4rem', fontWeight: 800, color: '#0d6efd', lineHeight: 1 }}>
      {value}
    </div>
    <div className="fw-semibold mt-2">{label}</div>
    {sub && <div className="text-muted small mt-1">{sub}</div>}
  </div>
);

const ElectionCard: React.FC<{ election: typeof ELECTIONS[0] }> = ({ election }) => (
  <a href="/simulation/compare" style={{ textDecoration: 'none' }}>
    <Card className="h-100 border-0 shadow-sm" style={{ cursor: 'pointer', transition: 'transform 0.15s' }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      <Card.Body className="p-3">
        <div className="d-flex align-items-start gap-2 mb-2">
          <span style={{ fontSize: '1.4rem' }}>{election.flag}</span>
          <div>
            <div className="fw-bold" style={{ fontSize: '0.9rem' }}>
              {election.name} {election.year}
              {election.badge && (
                <Badge bg={election.badge.bg} text="dark" className="ms-2" style={{ fontSize: '0.65rem' }}>
                  {election.badge.text}
                </Badge>
              )}
            </div>
            <div className="text-muted" style={{ fontSize: '0.75rem' }}>{election.country}</div>
          </div>
        </div>
        <p className="text-muted mb-0" style={{ fontSize: '0.8rem', lineHeight: 1.4 }}>
          {election.finding}
        </p>
      </Card.Body>
      <Card.Footer className="bg-transparent border-0 pt-0 pb-2 px-3">
        <small className="text-primary">Analyser →</small>
      </Card.Footer>
    </Card>
  </a>
);

// ── Main page ───────────────────────────────────────────────────────────────

const HomePage: React.FC = () => {
  const stats = useQuickStats();
  const [tourRun, setTourRun] = useState(false);

  const startTour = useCallback(() => {
    localStorage.removeItem('tour_completed'); // allow re-run
    setTourRun(false);
    setTimeout(() => setTourRun(true), 100);
  }, []);

  const handleTourFinish = useCallback(() => setTourRun(false), []);

  // Auto-start on first visit or when ?tour=1 is in the URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get('tour') === '1';
    const completed = localStorage.getItem('tour_completed');
    if (forced || !completed) {
      const t = setTimeout(() => setTourRun(true), 600);
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <div>
      <OnboardingTour run={tourRun} onFinish={handleTourFinish} />

      {/* ── Hero ── */}
      <div
        data-tour="hero"
        style={{ background: 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)', color: 'white' }}
        className="py-5"
      >
        <Container>
          <Row className="justify-content-center text-center py-4">
            <Col md={8} lg={7}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, letterSpacing: '0.1em', opacity: 0.8 }} className="mb-3 text-uppercase">
                Laboratoire civique de la démocratie
              </div>
              <h1 className="mb-3 fw-bold" style={{ fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', lineHeight: 1.2 }}>
                Testez comment votre bulletin de vote change tout
              </h1>
              <p className="mb-4 opacity-75" style={{ fontSize: '1.05rem' }}>
                15 méthodes de vote, des données électorales réelles, et une question fondamentale :
                et si le vote blanc pouvait réellement changer le résultat ?
              </p>
              <div className="d-flex gap-3 justify-content-center flex-wrap">
                <a href="/scenario-builder">
                  <Button variant="light" size="lg" className="fw-semibold px-4">
                    🗳️ Simuler une élection
                  </Button>
                </a>
                <a href="/simulation/compare">
                  <Button variant="outline-light" size="lg" className="px-4">
                    Comparer les méthodes
                  </Button>
                </a>
                <Button
                  variant="outline-light"
                  size="lg"
                  className="px-4"
                  onClick={startTour}
                  style={{ opacity: 0.85 }}
                >
                  🎓 Démarrer le tour
                </Button>
              </div>
            </Col>
          </Row>
        </Container>
      </div>

      {/* ── 3 Action cards ── */}
      <Container className="py-5">
        <Row className="g-4 mb-5">
          <Col md={4}>
            <ActionCard
              emoji="🗳️"
              title="Simuler une élection"
              description="Créez vos candidats, configurez l'électorat, ajoutez le vote blanc. Comparez comment 5 méthodes élisent des vainqueurs différents sur le même population."
              href="/scenario-builder"
              buttonText="Construire mon scénario"
              highlight
            />
          </Col>
          <Col md={4} data-tour="compare-card">
            <ActionCard
              emoji="⚖️"
              title="Comparer les méthodes"
              description="Pluralité, Borda, IRV, Schulze, Approbation — analysez leurs différences sur 15 dimensions : regret bayésien, critère de Condorcet, vulnérabilité stratégique."
              href="/simulation/compare"
              buttonText="Lancer la comparaison"
              variant="outline-primary"
            />
          </Col>
          <Col md={4} data-tour="blank-vote-card">
            <ActionCard
              emoji="⬜"
              title="Et si le vote blanc comptait ?"
              description="Que se passe-t-il si le vote blanc gagne ? Explorez 3 scénarios constitutionnels : nouvelle élection, gouvernement provisoire, dissolution proportionnelle."
              href="/constitutional-crisis"
              buttonText="Explorer les scénarios"
              variant="outline-warning"
            />
          </Col>
        </Row>

        {/* ── Pourquoi ça compte ── */}
        <div className="mb-5">
          <h2 className="fw-bold text-center mb-1">Pourquoi ça compte</h2>
          <p className="text-muted text-center mb-4">
            Statistiques calculées en temps réel sur une simulation aléatoire
          </p>
          <Row className="g-3">
            <Col md={4}>
              <StatCard
                value={
                  stats.loading ? (
                    <Spinner size="sm" />
                  ) : stats.disagreeingMethods !== null ? (
                    `${stats.disagreeingMethods}/${stats.totalMethods}`
                  ) : (
                    '?'
                  )
                }
                label="méthodes désaccord avec la pluralité"
                sub={
                  stats.loading
                    ? 'Simulation en cours…'
                    : stats.disagreeingMethods !== null
                    ? `Sur ${stats.totalMethods} méthodes testées avec 200 électeurs et 3 candidats`
                    : 'Backend non disponible'
                }
              />
            </Col>
            <Col md={4}>
              <StatCard
                value="15"
                label="méthodes de vote comparées"
                sub="Pluralité, Borda, IRV, Schulze, STAR, Condorcet, Médiane, Variance et plus"
              />
            </Col>
            <Col md={4}>
              <StatCard
                value={
                  stats.loading ? (
                    <Spinner size="sm" />
                  ) : stats.condorcetExists !== null ? (
                    stats.condorcetExists ? '✓' : '✗'
                  ) : (
                    '?'
                  )
                }
                label={stats.condorcetExists === false ? 'Pas de vainqueur de Condorcet' : 'Vainqueur de Condorcet'}
                sub={
                  stats.condorcetExists === false
                    ? 'Cycle détecté — la méthode de vote change le résultat'
                    : stats.condorcetExists === true
                    ? 'Un candidat bat tous les autres en duel direct'
                    : 'En attente de simulation…'
                }
              />
            </Col>
          </Row>
          <p className="text-muted text-center mt-3" style={{ fontSize: '0.8rem' }}>
            Rechargez la page pour une nouvelle simulation aléatoire
          </p>
        </div>

        {/* ── Historical elections ── */}
        <div data-tour="elections-section">
          <h2 className="fw-bold text-center mb-1">Élections historiques analysées</h2>
          <p className="text-muted text-center mb-4">
            Cliquez pour voir comment chaque méthode aurait modifié le résultat
          </p>
          <Row className="g-3">
            {ELECTIONS.map((e) => (
              <Col key={e.key} xs={12} sm={6} md={3}>
                <ElectionCard election={e} />
              </Col>
            ))}
          </Row>
          <div className="text-center mt-3">
            <a href="/simulation/compare">
              <Button variant="link" className="text-muted">
                Ouvrir l'onglet "Élections réelles" pour analyser →
              </Button>
            </a>
          </div>
        </div>
      </Container>

      {/* ── Footer strip ── */}
      <div className="border-top py-3 mt-3" style={{ backgroundColor: '#f8f9fa' }}>
        <Container>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span className="text-muted small">
              🗳️ <strong>Vote Lab</strong> — Laboratoire civique open-source
            </span>
            <div className="d-flex gap-3">
              <a href="/simulation" className="text-muted small">Outil avancé (connexion requise)</a>
              <a href="/login" className="text-muted small">Connexion</a>
              <a href="/register" className="text-muted small">Créer un compte</a>
            </div>
          </div>
        </Container>
      </div>
    </div>
  );
};

export default HomePage;
