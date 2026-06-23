import React from 'react';
import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useElection, usePlayground } from '../stores/useElectionStore';
import { useMetaTags } from '../hooks/useMetaTags';
import CampaignTimeline from '../components/campaign/CampaignTimeline';

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
// Structure: the inherited J0 electorate, then the unified timeline (C2,
// continuous days + discrete rounds → live value-of-the-result), then three
// lazy/Collapsible-gated families migrated off the playground:
//   • CampaignAnchor (C1) — Hotelling, polls, polarization, party dynamics;
//   • TemporalDynamicsAnchor (C3) — adaptive/replay/primary + cascade/fatigue;
//   • BehavioralRealismAnchor (C4) — single-ballot B realism (biases, shy voter,
//     overload, compulsory, demographic, affective).
// The playground now keeps only the idealized snapshot (family A).

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
    <div className="container mx-auto max-w-6xl px-3 py-4" data-testid="campaign-dynamics-page">
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

      {/* ── Deep-dive anchor (C1): the migrated temporal panels (Hotelling,
          polls, polarization, party dynamics). ── */}
      {hasElectorate && (
        <Card className="mb-4" data-testid="campaign-dynamics-core">
          <CardHeader>
            <CardTitle className="text-base">🎬 Approfondir la trajectoire</CardTitle>
          </CardHeader>
          <CardContent>
            <React.Suspense fallback={<AnchorFallback />}>
              <CampaignAnchor />
            </React.Suspense>
          </CardContent>
        </Card>
      )}

      {/* ── Temporal mechanisms + sequential behaviour (C3): migrated off the
          playground — they unfold over rounds/sequence, like the timeline. ── */}
      {hasElectorate && (
        <Card className="mb-4" data-testid="campaign-temporal-mechanisms">
          <CardHeader>
            <CardTitle className="text-base">
              🔁 Mécanismes &amp; comportements dans le temps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <React.Suspense fallback={<AnchorFallback />}>
              <TemporalDynamicsAnchor />
            </React.Suspense>
          </CardContent>
        </Card>
      )}

      {/* ── Behavioural realism (C4): the family-B single-ballot deformations,
          migrated off the playground as a secondary "réalisme" facette. ── */}
      {hasElectorate && (
        <Card data-testid="campaign-behavioral-realism">
          <CardHeader>
            <CardTitle className="text-base">🧠 Réalisme comportemental (un scrutin)</CardTitle>
          </CardHeader>
          <CardContent>
            <React.Suspense fallback={<AnchorFallback />}>
              <BehavioralRealismAnchor />
            </React.Suspense>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CampaignDynamicsPage;
