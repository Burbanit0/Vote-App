/**
 * TheoryPage — voting-theory exploration hub.
 *
 * Three sections: (1) impossibility & paradoxes — pure theory,
 * (2) power & justice — normative critiques, (3) practical limits
 * — panels that ALSO exist in the Lab (with a deep-link back to
 * the relevant Lab tab so the user understands "this is the theory
 * version; apply it to your election in the Lab").
 *
 * The disambiguation banner at the top explains the distinction
 * between Theory (standalone illustrations) and Lab (apply to a
 * configured baseline election).
 */
import React from 'react';
import { Link } from 'react-router';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import { PageContainer } from '../theme';
import ArrowExplorer from '../components/Simulation/ArrowExplorer';
import PlottChaosPanel from '../components/Simulation/PlottChaosPanel';
import JudgmentAggregationPanel from '../components/shared/JudgmentAggregationPanel';
import SenParadoxPanel from '../components/shared/SenParadoxPanel';
import ApportionmentPanel from '../components/shared/ApportionmentPanel';
import AgendaManipulationPanel from '../components/shared/AgendaManipulationPanel';
import MajorityTyrannyPanel from '../components/shared/MajorityTyrannyPanel';
import PowerIndicesPanel from '../components/shared/PowerIndicesPanel';
import DemocraticBackslidingPanel from '../components/shared/DemocraticBackslidingPanel';
import IntergenerationalPanel from '../components/shared/IntergenerationalPanel';
import EpistocracyPanel from '../components/shared/EpistocracyPanel';
import IdentityVotingPanel from '../components/shared/IdentityVotingPanel';
import AssumptionTesterPanel from '../components/shared/AssumptionTesterPanel';
import CollectiveWillPanel from '../components/shared/CollectiveWillPanel';

// ── Panel registry ──────────────────────────────────────────────────────────
// `labTab` (when set) names the corresponding Election Lab tab so the user
// can jump from the theoretical view to the configured-election view.

interface PanelMeta {
  id:      string;
  icon:    string;
  titleK:  string;
  descK:   string;
  border:  string;
  color?:  string;
  labTab?: string;
  body:    React.ReactNode;
}

const SECTIONS: { id: string; titleK: string; subtitleK: string; panels: PanelMeta[] }[] = [
  {
    id:        'impossibility',
    titleK:    'theory.section.impossibility.title',
    subtitleK: 'theory.section.impossibility.subtitle',
    panels: [
      { id: 'arrow', icon: '🏛', titleK: 'arrow.pageTitle', descK: 'arrow.pageSubtitle',
        border: '#0d6efd', color: '#0d6efd', body: <ArrowExplorer /> },
      { id: 'plott', icon: '🌀', titleK: 'plott.cardTitle', descK: 'plott.cardDesc',
        border: '#dc3545', color: '#dc3545', body: <PlottChaosPanel /> },
      { id: 'sen', icon: '⚖️', titleK: 'sen.cardTitle', descK: 'sen.cardDesc',
        border: '#ffc107', color: '#856404', body: <SenParadoxPanel /> },
      { id: 'judgment', icon: '⚖️', titleK: 'judg.cardTitle', descK: 'judg.cardDesc',
        border: '#0dcaf0', color: '#0dcaf0', body: <JudgmentAggregationPanel /> },
      { id: 'agenda', icon: '🗓', titleK: 'agenda.cardTitle', descK: 'agenda.cardDesc',
        border: '#212529', body: <AgendaManipulationPanel /> },
      { id: 'apportionment', icon: '📊', titleK: 'appor.cardTitle', descK: 'appor.cardDesc',
        border: '#6c757d', body: <ApportionmentPanel /> },
    ],
  },
  {
    id:        'power-justice',
    titleK:    'theory.section.powerJustice.title',
    subtitleK: 'theory.section.powerJustice.subtitle',
    panels: [
      { id: 'power', icon: '⚡', titleK: 'power.cardTitle', descK: 'power.cardDesc',
        border: '#198754', color: '#198754', body: <PowerIndicesPanel /> },
      { id: 'tyranny', icon: '👑', titleK: 'tyranny.cardTitle', descK: 'tyranny.cardDesc',
        border: '#6f1d1b', color: '#6f1d1b', body: <MajorityTyrannyPanel /> },
      { id: 'backsliding', icon: '🏚', titleK: 'backsliding.cardTitle', descK: 'backsliding.cardDesc',
        border: '#842029', color: '#842029', body: <DemocraticBackslidingPanel /> },
      { id: 'intergen', icon: '🌱', titleK: 'intergen.cardTitle', descK: 'intergen.cardDesc',
        border: '#0d6efd', color: '#0d6efd', body: <IntergenerationalPanel /> },
    ],
  },
  {
    id:        'practical',
    titleK:    'theory.section.practical.title',
    subtitleK: 'theory.section.practical.subtitle',
    panels: [
      { id: 'identity', icon: '🏳', titleK: 'identity.cardTitle', descK: 'identity.cardDesc',
        border: '#6610f2', color: '#6610f2', labTab: 'lab-identity',
        body: <IdentityVotingPanel /> },
      { id: 'episto', icon: '🎓', titleK: 'episto.cardTitle', descK: 'episto.cardDesc',
        border: '#ffc107', color: '#856404', labTab: 'lab-epistocracy',
        body: <EpistocracyPanel /> },
      { id: 'will', icon: '🌊', titleK: 'will.cardTitle', descK: 'will.cardDesc',
        border: '#495057', color: '#495057', labTab: 'lab-collective-will',
        body: <CollectiveWillPanel /> },
      { id: 'assumptions', icon: '🔬', titleK: 'assumptions.cardTitle', descK: 'assumptions.cardDesc',
        border: '#6c757d', color: '#6c757d', labTab: 'lab-assumptions',
        body: <AssumptionTesterPanel /> },
    ],
  },
];

const TheoryPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Théorie du vote — Vote Lab',
    description: "Explorez le théorème d'impossibilité d'Arrow et les paradoxes de la théorie du choix social.",
  });

  return (
    <PageContainer variant="wide">
      <h2 className="mb-1 text-[1.5rem] font-bold">🏛 {t('theory.pageTitle')}</h2>
      <p className="mb-4 text-[0.9rem] text-muted-foreground">
        {t('theory.pageSubtitle')}
      </p>

      {/* ── Disambiguation banner — clarifies Theory vs Lab ── */}
      <Card
        className="mb-6"
        data-testid="theory-disambig-banner"
        style={{ background: '#fff8e1', borderColor: '#f9a825' }}
      >
        <CardContent className="p-6 py-4 text-[0.85rem]">
          <div className="mb-1 font-bold">💡 {t('theory.disambig.title')}</div>
          <div>{t('theory.disambig.body')}</div>
          <div className="mt-2">
            <Button asChild variant="outline" size="sm">
              <Link to="/election-lab">{t('theory.disambig.cta')} →</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── Table of contents ── */}
      <Card className="mb-6" data-testid="theory-toc">
        <CardHeader className="p-6 py-2 text-[0.85rem] font-semibold">
          📑 {t('theory.toc')}
        </CardHeader>
        <CardContent className="p-6 py-2 text-[0.85rem]">
          <nav className="flex flex-col flex-wrap gap-2 md:flex-row">
            {SECTIONS.flatMap((section) =>
              section.panels.map((p) => (
                <a
                  key={p.id}
                  href={`#panel-${p.id}`}
                  className="rounded border border-border bg-muted px-2 py-1 no-underline"
                >
                  {p.icon} {t(p.titleK)}
                </a>
              ))
            )}
          </nav>
        </CardContent>
      </Card>

      {/* ── Sections ── */}
      {SECTIONS.map((section) => (
        <section key={section.id} id={`section-${section.id}`} className="mb-12">
          <h4 className="mb-1 text-xl font-bold" data-testid={`section-${section.id}`}>
            {t(section.titleK)}
          </h4>
          <p className="mb-4 text-[0.85rem] text-muted-foreground">
            {t(section.subtitleK)}
          </p>
          {section.panels.map((p) => (
            <Card
              key={p.id}
              id={`panel-${p.id}`}
              className="mb-6"
              style={{ borderColor: p.border, scrollMarginTop: 80 }}
              data-testid={`panel-${p.id}`}
            >
              <CardHeader
                className="flex flex-row flex-wrap items-center justify-between gap-2 p-6 font-bold"
                style={{ color: p.color }}
              >
                <span>{p.icon} {t(p.titleK)}</span>
                {p.labTab && (
                  <Link
                    to={`/election-lab?tab=${p.labTab}`}
                    className="no-underline"
                    data-testid={`also-in-lab-${p.id}`}
                  >
                    <Badge className="rounded-full text-[0.7rem]">
                      🔬 {t('theory.alsoInLab')} →
                    </Badge>
                  </Link>
                )}
              </CardHeader>
              <CardContent className="p-6 pt-0">
                <p className="text-[0.85rem]">{t(p.descK)}</p>
                {p.body}
              </CardContent>
            </Card>
          ))}
        </section>
      ))}
    </PageContainer>
  );
};

export default TheoryPage;
