import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Loader2 } from 'lucide-react';
import { runComparisonSimulation } from '../services/simulationCompareApi';
import OnboardingTour from '../components/shared/OnboardingTour';
import QuickCompareWidget from '../components/shared/QuickCompareWidget';
import { useMetaTags } from '../hooks/useMetaTags';
import { useTranslation } from 'react-i18next';
import { useElection } from '../stores/useElectionStore';
import { Button } from '@/components/ui/button';

// ── Tailwind-migrated (Phase 6) ──────────────────────────────────────────────
// Off react-bootstrap → Tailwind utilities + shadcn Button. Bootstrap spacing
// (3=1rem, 4=1.5rem, 5=3rem) is converted to Tailwind's scale (4=1rem, 6=1.5rem,
// 12=3rem). data-style="tailwind" marks migrated screens.

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
          setState({
            disagreeingMethods: null,
            totalMethods: 15,
            condorcetExists: null,
            loading: false,
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

const Spinner = () => <Loader2 className="inline h-4 w-4 animate-spin" aria-label="loading" />;

// ── Stat card ───────────────────────────────────────────────────────────────

const StatCard: React.FC<{ value: React.ReactNode; label: string; sub?: string }> = ({
  value,
  label,
  sub,
}) => (
  <div className="rounded-lg bg-muted px-4 py-6 text-center">
    <div className="text-[2.4rem] font-extrabold leading-none text-[#0d6efd]">{value}</div>
    <div className="mt-2 font-semibold">{label}</div>
    {sub && <div className="mt-1 text-sm text-muted-foreground">{sub}</div>}
  </div>
);

// ── Feature item ────────────────────────────────────────────────────────────

const FeatureItem: React.FC<{
  icon: string;
  title: string;
  desc: string;
  href?: string;
  onClick?: () => void;
}> = ({ icon, title, desc, href, onClick }) => (
  <div
    className="flex cursor-pointer items-start gap-4 rounded-lg bg-muted p-4 transition-colors hover:bg-accent"
    onClick={
      onClick ??
      (() => {
        if (href) window.location.href = href;
      })
    }
    role="button"
    tabIndex={0}
    onKeyDown={(e) => {
      if (e.key === 'Enter') {
        if (onClick) onClick();
        else if (href) window.location.href = href;
      }
    }}
  >
    <span className="shrink-0 text-[1.8rem]">{icon}</span>
    <div>
      <div className="text-[0.9rem] font-semibold">{title}</div>
      <div className="text-[0.8rem] leading-snug text-muted-foreground">{desc}</div>
    </div>
  </div>
);

// ── Main page ───────────────────────────────────────────────────────────────

const HomePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { applyScenario } = useElection();
  const stats = useQuickStats();
  const [tourRun, setTourRun] = useState(false);

  useMetaTags({
    title: `Vote Lab — ${t('home.heroTitle')}`,
    description: t('home.heroParagraph'),
  });

  const startTour = useCallback(() => {
    localStorage.removeItem('tour_completed');
    setTourRun(false);
    setTimeout(() => setTourRun(true), 100);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get('tour') === '1';
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
    <div data-style="tailwind">
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero — compact ── */}
      <div
        data-tour="hero"
        className="bg-gradient-to-br from-[#0d6efd] to-[#0a58ca] py-12 text-white"
      >
        <div className="mx-auto w-full max-w-[1140px] px-4">
          <div className="flex flex-wrap justify-center py-4 text-center">
            <div className="mx-auto max-w-2xl">
              <div className="mb-4 text-[0.85rem] font-semibold uppercase tracking-[0.1em] opacity-80">
                {t('home.heroBadge')}
              </div>
              <h1 className="mb-4 font-bold leading-tight text-[clamp(1.6rem,4vw,2.4rem)]">
                {t('home.heroTitle')}
              </h1>
              <p className="mb-6 text-base opacity-75">{t('home.heroParagraph')}</p>
              <div className="flex flex-wrap justify-center gap-4">
                <Button
                  size="lg"
                  className="bg-white px-6 font-semibold text-slate-900 hover:bg-white/90"
                  onClick={goToLab}
                >
                  🔬 {t('home.ctaLab')}
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white/60 bg-transparent px-4 text-white opacity-85 hover:bg-white/10 hover:text-white"
                  onClick={startTour}
                >
                  {t('home.ctaTour')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1140px] px-4 py-12">
        {/* ── Section 2: QuickCompare widget ── */}
        <div className="mb-12">
          <QuickCompareWidget />
        </div>

        {/* ── Playground CTA (Lab reshape) ── */}
        <div className="mb-12 flex flex-col items-center gap-3 rounded-xl border border-border bg-muted/30 px-4 py-6 text-center">
          <div className="text-3xl">🎛</div>
          <h2 className="text-xl font-bold">Playground</h2>
          <p className="max-w-xl text-[0.9rem] text-muted-foreground">
            Un même électorat, deux questions : élire un dirigeant ou composer un parlement.
            Basculez de l’un à l’autre et regardez le caractère politique s’inverser.
          </p>
          <Button variant="primary" onClick={() => navigate('/playground')}>
            Ouvrir le Playground →
          </Button>
        </div>

        {/* ── Section 3: 3 feature items ── */}
        <div className="mb-12">
          <h2 className="mb-1 text-center text-xl font-bold">{t('home.featuresTitle')}</h2>
          <p className="mb-6 text-center text-[0.88rem] text-muted-foreground">
            {t('home.featuresSubtitle')}
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <FeatureItem
              icon="🔬"
              title={t('home.feature1Title')}
              desc={t('home.feature1Desc')}
              onClick={() => navigate('/election-lab')}
            />
            <FeatureItem
              icon="📊"
              title={t('home.feature2Title')}
              desc={t('home.feature2Desc')}
              onClick={() => {
                applyScenario('france2002');
                navigate('/election-lab');
              }}
            />
            <FeatureItem
              icon="🎓"
              title={t('home.feature3Title')}
              desc={t('home.feature3Desc')}
              href="/?tour=1"
            />
          </div>
        </div>

        {/* ── Section 4: Live stats ── */}
        <div className="mb-2">
          <h2 className="mb-1 text-center font-bold">{t('home.whySectionTitle')}</h2>
          <p className="mb-6 text-center text-muted-foreground">{t('home.whySectionSubtitle')}</p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard
              value={
                stats.loading ? (
                  <Spinner />
                ) : stats.disagreeingMethods !== null ? (
                  `${stats.disagreeingMethods}/${stats.totalMethods}`
                ) : (
                  '?'
                )
              }
              label={t('home.statDisagree')}
              sub={
                stats.loading
                  ? t('home.statLoading')
                  : stats.disagreeingMethods !== null
                    ? t('home.statDisagreeSub', { total: stats.totalMethods })
                    : t('home.statBackendDown')
              }
            />
            <StatCard
              value="15"
              label={t('home.statMethodsCompared')}
              sub={t('home.statMethodsSub')}
            />
            <StatCard
              value={
                stats.loading ? (
                  <Spinner />
                ) : stats.condorcetExists !== null ? (
                  stats.condorcetExists ? (
                    '✓'
                  ) : (
                    '✗'
                  )
                ) : (
                  '?'
                )
              }
              label={
                stats.condorcetExists === false
                  ? t('home.statNoCondorcet')
                  : t('home.statCondorcetExists')
              }
              sub={
                stats.condorcetExists === false
                  ? t('home.statCycle')
                  : stats.condorcetExists === true
                    ? t('home.statCondorcetDesc')
                    : t('home.statWaiting')
              }
            />
          </div>
          <p className="mt-4 text-center text-[0.8rem] text-muted-foreground">
            {t('home.reloadPrompt')}
          </p>
        </div>
      </div>

      {/* ── Footer strip ── */}
      <div className="mt-4 border-t border-border bg-muted py-4">
        <div className="mx-auto w-full max-w-[1140px] px-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm text-muted-foreground">
              🗳️ <strong>Vote Lab</strong>
              {t('home.footer')}
            </span>
            <div className="flex gap-4">
              <a href="/simulation" className="text-sm text-muted-foreground">
                {t('home.footerAdvanced')}
              </a>
              <a href="/login" className="text-sm text-muted-foreground">
                {t('home.footerLogin')}
              </a>
              <a href="/register" className="text-sm text-muted-foreground">
                {t('home.footerSignup')}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
