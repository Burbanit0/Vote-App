import React, { useCallback, useEffect, useState } from 'react';
import { Button, Col, Container, Row, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router';
import { runComparisonSimulation } from '../services/simulationCompareApi';
import OnboardingTour from '../components/shared/OnboardingTour';
import QuickCompareWidget from '../components/shared/QuickCompareWidget';
import { useMetaTags } from '../hooks/useMetaTags';
import { useTranslation } from 'react-i18next';
import { useElection } from '../context/ElectionContext';

// ── Dynamic stats hook ──────────────────────────────────────────────────────

interface QuickStats {
  disagreeingMethods: number | null;
  totalMethods: number;
  condorcetExists: boolean | null;
  loading: boolean;
}

function useQuickStats(): QuickStats {
  const [state, setState] = useState<QuickStats>({
    disagreeingMethods: null, totalMethods: 15,
    condorcetExists: null, loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    runComparisonSimulation({ num_voters: 200, candidates: ['Alice', 'Bob', 'Charlie'] })
      .then((r) => {
        if (cancelled) return;
        const methods        = Object.values(r.methods);
        const pluralityWinner = r.methods['plurality']?.winner;
        const disagreeing    = methods.filter(
          (m) => m.winner !== null && m.winner !== pluralityWinner
        ).length;
        setState({ disagreeingMethods: disagreeing, totalMethods: methods.length,
                   condorcetExists: r.condorcet_winner !== null, loading: false });
      })
      .catch(() => {
        if (!cancelled)
          setState({ disagreeingMethods: null, totalMethods: 15, condorcetExists: null, loading: false });
      });
    return () => { cancelled = true; };
  }, []);

  return state;
}

// ── Stat card ───────────────────────────────────────────────────────────────

const StatCard: React.FC<{ value: React.ReactNode; label: string; sub?: string }> = ({ value, label, sub }) => (
  <div className="text-center px-3 py-4 rounded-3" style={{ backgroundColor: 'var(--bs-secondary-bg)' }}>
    <div style={{ fontSize: '2.4rem', fontWeight: 800, color: '#0d6efd', lineHeight: 1 }}>{value}</div>
    <div className="fw-semibold mt-2">{label}</div>
    {sub && <div className="text-muted small mt-1">{sub}</div>}
  </div>
);

// ── Feature item ────────────────────────────────────────────────────────────

const FeatureItem: React.FC<{
  icon: string; title: string; desc: string;
  href?: string; onClick?: () => void;
}> = ({ icon, title, desc, href, onClick }) => (
  <div
    className="d-flex align-items-start gap-3 p-3 rounded-3"
    style={{ background: 'var(--bs-secondary-bg, #f8f9fa)', cursor: 'pointer', transition: 'background 0.15s' }}
    onClick={onClick ?? (() => { if (href) window.location.href = href; })}
    role="button"
    tabIndex={0}
    onKeyDown={(e) => { if (e.key === 'Enter') { if (onClick) onClick(); else if (href) window.location.href = href; } }}
  >
    <span style={{ fontSize: '1.8rem', flexShrink: 0 }}>{icon}</span>
    <div>
      <div className="fw-semibold" style={{ fontSize: '0.9rem' }}>{title}</div>
      <div className="text-muted" style={{ fontSize: '0.8rem', lineHeight: 1.4 }}>{desc}</div>
    </div>
  </div>
);

// ── Main page ───────────────────────────────────────────────────────────────

const HomePage: React.FC = () => {
  const { t }      = useTranslation();
  const navigate   = useNavigate();
  const { applyScenario } = useElection();
  const stats      = useQuickStats();
  const [tourRun,  setTourRun]  = useState(false);

  useMetaTags({
    title:       `Vote Lab — ${t('home.heroTitle')}`,
    description: t('home.heroParagraph'),
  });

  const startTour = useCallback(() => {
    localStorage.removeItem('tour_completed');
    setTourRun(false);
    setTimeout(() => setTourRun(true), 100);
  }, []);

  useEffect(() => {
    const params    = new URLSearchParams(window.location.search);
    const forced    = params.get('tour') === '1';
    const completed = localStorage.getItem('tour_completed');
    if (forced || !completed) {
      const t2 = setTimeout(() => setTourRun(true), 600);
      return () => clearTimeout(t2);
    }
  }, []);

  const goToLab = useCallback(() => {
    applyScenario('france2002');
    navigate('/election-lab');
  }, [applyScenario, navigate]);

  return (
    <div>
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero — compact ── */}
      <div
        data-tour="hero"
        style={{ background: 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)', color: 'white' }}
        className="py-5"
      >
        <Container>
          <Row className="justify-content-center text-center py-3">
            <Col md={8} lg={6}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.1em', opacity: 0.8 }}
                className="mb-3 text-uppercase">
                {t('home.heroBadge')}
              </div>
              <h1 className="mb-3 fw-bold" style={{ fontSize: 'clamp(1.6rem, 4vw, 2.4rem)', lineHeight: 1.2 }}>
                {t('home.heroTitle')}
              </h1>
              <p className="mb-4 opacity-75" style={{ fontSize: '1rem' }}>
                {t('home.heroParagraph')}
              </p>
              <div className="d-flex gap-3 justify-content-center flex-wrap">
                <Button variant="light" size="lg" className="fw-semibold px-4" onClick={goToLab}>
                  🔬 {t('home.ctaLab')}
                </Button>
                <Button variant="outline-light" size="lg" className="px-3" onClick={startTour}
                  style={{ opacity: 0.85 }}>
                  {t('home.ctaTour')}
                </Button>
              </div>
            </Col>
          </Row>
        </Container>
      </div>

      <Container className="py-5">
        {/* ── Section 2: QuickCompare widget ── */}
        <div className="mb-5">
          <QuickCompareWidget />
        </div>

        {/* ── Section 3: 3 feature items ── */}
        <div className="mb-5">
          <h2 className="fw-bold text-center mb-1" style={{ fontSize: '1.25rem' }}>
            {t('home.featuresTitle')}
          </h2>
          <p className="text-muted text-center mb-4" style={{ fontSize: '0.88rem' }}>
            {t('home.featuresSubtitle')}
          </p>
          <Row className="g-3">
            <Col xs={12} md={4}>
              <FeatureItem
                icon="🔬"
                title={t('home.feature1Title')}
                desc={t('home.feature1Desc')}
                onClick={() => navigate('/election-lab')}
              />
            </Col>
            <Col xs={12} md={4}>
              <FeatureItem
                icon="📊"
                title={t('home.feature2Title')}
                desc={t('home.feature2Desc')}
                onClick={() => { applyScenario('france2002'); navigate('/election-lab'); }}
              />
            </Col>
            <Col xs={12} md={4}>
              <FeatureItem
                icon="🎓"
                title={t('home.feature3Title')}
                desc={t('home.feature3Desc')}
                href="/?tour=1"
              />
            </Col>
          </Row>
        </div>

        {/* ── Section 4: Live stats ── */}
        <div className="mb-2">
          <h2 className="fw-bold text-center mb-1">{t('home.whySectionTitle')}</h2>
          <p className="text-muted text-center mb-4">{t('home.whySectionSubtitle')}</p>
          <Row className="g-3">
            <Col md={4}>
              <StatCard
                value={stats.loading ? <Spinner size="sm" />
                  : stats.disagreeingMethods !== null ? `${stats.disagreeingMethods}/${stats.totalMethods}` : '?'}
                label={t('home.statDisagree')}
                sub={stats.loading ? t('home.statLoading')
                  : stats.disagreeingMethods !== null ? t('home.statDisagreeSub', { total: stats.totalMethods })
                  : t('home.statBackendDown')}
              />
            </Col>
            <Col md={4}>
              <StatCard value="15" label={t('home.statMethodsCompared')} sub={t('home.statMethodsSub')} />
            </Col>
            <Col md={4}>
              <StatCard
                value={stats.loading ? <Spinner size="sm" />
                  : stats.condorcetExists !== null ? (stats.condorcetExists ? '✓' : '✗') : '?'}
                label={stats.condorcetExists === false ? t('home.statNoCondorcet') : t('home.statCondorcetExists')}
                sub={stats.condorcetExists === false ? t('home.statCycle')
                  : stats.condorcetExists === true ? t('home.statCondorcetDesc')
                  : t('home.statWaiting')}
              />
            </Col>
          </Row>
          <p className="text-muted text-center mt-3" style={{ fontSize: '0.8rem' }}>
            {t('home.reloadPrompt')}
          </p>
        </div>
      </Container>

      {/* ── Footer strip ── */}
      <div className="border-top py-3 mt-3" style={{ backgroundColor: 'var(--bs-secondary-bg, #f8f9fa)' }}>
        <Container>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span className="text-muted small">
              🗳️ <strong>Vote Lab</strong>
              {t('home.footer')}
            </span>
            <div className="d-flex gap-3">
              <a href="/simulation" className="text-muted small">{t('home.footerAdvanced')}</a>
              <a href="/login"      className="text-muted small">{t('home.footerLogin')}</a>
              <a href="/register"   className="text-muted small">{t('home.footerSignup')}</a>
            </div>
          </div>
        </Container>
      </div>
    </div>
  );
};

export default HomePage;
