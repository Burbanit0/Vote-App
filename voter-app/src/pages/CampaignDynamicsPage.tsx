import React from 'react';
import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useElection, usePlayground } from '../stores/useElectionStore';
import { useMetaTags } from '../hooks/useMetaTags';
import CampaignTimeline from '../components/campaign/CampaignTimeline';
import Collapsible from '../components/playground/Collapsible';

// CampaignDynamicsPage — page 2 of the journey ("Campagne & dynamique").
//
// Where the playground answers the STATIC question ("for this electorate, how do
// the methods differ?"), this page answers the DYNAMIC one ("how does the vote
// EVOLVE over time — campaign drift, mind-changes, real behaviour?").
//
// Hand-off (Q3 = sandbox): it READS the shared electorate (`config` = state J0)
// and the playground knobs from the store — opening or playing with this page
// leaves the playground untouched. The single exception is the explicit "pin"
// action on the timeline, which writes the current drifted positions back as the
// new baseline (carry the campaign's end-state into the snapshot tools).
//
// Organised like the playground: the inherited J0 electorate, then the central
// INSTRUMENT (CampaignTimeline — a scenario rail + two synced graphs that move as
// you scrub), then ONE collapsed "Explorations approfondies" drawer holding the
// deep per-phenomenon panels (CampaignAnchor, TemporalDynamicsAnchor,
// BehavioralRealismAnchor) — demoted, lazy, never competing with the instrument.
// The playground keeps only the idealized snapshot (family A).

const CampaignAnchor = React.lazy(() => import('../components/playground/anchors/CampaignAnchor'));
const TemporalDynamicsAnchor = React.lazy(
  () => import('../components/campaign/TemporalDynamicsAnchor')
);
const BehavioralRealismAnchor = React.lazy(
  () => import('../components/campaign/BehavioralRealismAnchor')
);

const AnchorFallback: React.FC = () => (
  <p className="p-2 text-xs text-muted-foreground">Chargement…</p>
);

const CampaignDynamicsPage: React.FC = () => {
  useMetaTags({
    title: 'Campagne & dynamique — comment le vote évolue dans le temps',
    description:
      'À partir de l’électorat composé dans le playground (état J0), perturbez le résultat : dérive de campagne, sondages, polarisation, dynamique des partis — et observez la valeur du résultat évoluer.',
  });

  // Sandbox by default (Q3): only the explicit "pin" action writes back.
  const { config, setConfig } = useElection();
  const { playground } = usePlayground();
  const { candidates, num_voters, ideology } = config;
  const hasElectorate = candidates.length > 0;

  // "Pin this instant back into the playground": carry the drifted positions
  // forward as the new baseline electorate (the one explicit write-back).
  const pinToPlayground = React.useCallback(
    (pinned: { name: string; x: number; y: number; z?: number }[]) => {
      setConfig({
        candidates: pinned.map((c) => ({ name: c.name, x: c.x, y: c.y, z: c.z })),
      });
    },
    [setConfig]
  );

  return (
    <div className="container mx-auto px-3 py-4" data-testid="campaign-dynamics-page">
      {/* ── Header ── */}
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-bold">📈 Campagne &amp; dynamique</h1>
          <Badge variant="secondary" data-testid="sandbox-badge">
            bac à sable
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Le playground donne un instantané idéalisé. Ici, on le perturbe dans le temps — dérive de
          campagne, sondages, polarisation, dynamique des partis. L’électorat est{' '}
          <strong>hérité du playground</strong> comme état de départ (J0) ; rien n’est modifié en
          retour.
        </p>
        <Link
          to="/playground"
          data-testid="back-to-playground"
          className="self-start text-sm text-primary hover:underline"
        >
          ← Revenir au playground
        </Link>
      </div>

      {/* ── Inherited electorate (J0) ── */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="text-base">Électorat hérité (état J0)</CardTitle>
        </CardHeader>
        <CardContent>
          {hasElectorate ? (
            <div className="flex flex-col gap-2 text-sm" data-testid="inherited-electorate">
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
                <span>
                  <strong className="text-foreground">{candidates.length}</strong>{' '}
                  {playground.mode === 'parliament' ? 'partis' : 'candidats'}
                </span>
                <span>
                  <strong className="text-foreground">{num_voters}</strong> électeurs
                </span>
                <span>
                  idéologie : <strong className="text-foreground">{ideology}</strong>
                </span>
                <span>
                  mode : <strong className="text-foreground">{playground.mode}</strong>
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {candidates.map((c) => (
                  <Badge key={c.name} variant="outline" className="font-normal">
                    {c.name}
                  </Badge>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground" data-testid="empty-electorate">
              Aucun électorat n’est encore configuré.{' '}
              <Link to="/playground" className="text-primary hover:underline">
                Composez-en un dans le playground
              </Link>
              , puis revenez lancer une campagne.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Timeline (C2): the unified time axis — continuous days + discrete
          rounds — driving the live "value of the result". ── */}
      {hasElectorate && (
        <Card className="mb-4" data-testid="campaign-timeline-card">
          <CardHeader>
            <CardTitle className="text-base">
              🕰️ Timeline — la valeur du résultat dans le temps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CampaignTimeline config={config} playground={playground} onPin={pinToPlayground} />
          </CardContent>
        </Card>
      )}

      {/* ── One demoted drawer (like the playground's Explorations row): the deep
          per-phenomenon panels stay reachable but never compete with the central
          instrument above. Collapsed + lazy → first paint mounts none of them. ── */}
      {hasElectorate && (
        <Collapsible
          title="🔬 Explorations approfondies"
          subtitle="trajectoire · mécanismes temporels · réalisme comportemental"
          testid="campaign-explorations"
        >
          <div className="flex flex-col gap-5">
            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">🎬 Approfondir la trajectoire</h3>
              <React.Suspense fallback={<AnchorFallback />}>
                <CampaignAnchor />
              </React.Suspense>
            </section>
            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">
                🔁 Mécanismes &amp; comportements dans le temps
              </h3>
              <React.Suspense fallback={<AnchorFallback />}>
                <TemporalDynamicsAnchor />
              </React.Suspense>
            </section>
            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">🧠 Réalisme comportemental (un scrutin)</h3>
              <React.Suspense fallback={<AnchorFallback />}>
                <BehavioralRealismAnchor />
              </React.Suspense>
            </section>
          </div>
        </Collapsible>
      )}
    </div>
  );
};

export default CampaignDynamicsPage;
