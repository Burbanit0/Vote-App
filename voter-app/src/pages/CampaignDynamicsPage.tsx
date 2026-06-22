import React from 'react';
import { Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useElection, usePlayground } from '../stores/useElectionStore';
import { useMetaTags } from '../hooks/useMetaTags';

// CampaignDynamicsPage — page 2 of the journey ("Campagne & dynamique").
//
// Where the playground answers the STATIC question ("for this electorate, how do
// the methods differ?"), this page answers the DYNAMIC one ("how does the vote
// EVOLVE over time — campaign drift, mind-changes, real behaviour?").
//
// Hand-off (Q3 = sandbox): it READS the shared electorate (`config` = state J0)
// and the playground knobs from the store, and never mutates them — opening or
// playing with this page leaves the playground untouched. The store is the only
// channel, so there is zero re-entry of the electorate.
//
// C1 (this commit) is the shell + hand-off: it inherits J0, shows it, and hosts
// the temporal CampaignAnchor (Hotelling, polls, polarization, party dynamics)
// migrated off the playground. C2 adds the unified timeline (continuous days +
// discrete rounds) above it; C3/C4 migrate the remaining temporal + behavioural
// panels here.

const CampaignAnchor = React.lazy(() => import('../components/playground/anchors/CampaignAnchor'));

const AnchorFallback: React.FC = () => (
  <p className="p-2 text-xs text-muted-foreground">Chargement…</p>
);

const CampaignDynamicsPage: React.FC = () => {
  useMetaTags({
    title: 'Campagne & dynamique — comment le vote évolue dans le temps',
    description:
      'À partir de l’électorat composé dans le playground (état J0), perturbez le résultat : dérive de campagne, sondages, polarisation, dynamique des partis — et observez la valeur du résultat évoluer.',
  });

  // Read-only hand-off — never call a setter here (sandbox / Q3).
  const { config } = useElection();
  const { playground } = usePlayground();
  const { candidates, num_voters, ideology } = config;
  const hasElectorate = candidates.length > 0;

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
            <div className="flex flex-col gap-2 text-sm">
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

      {/* ── Dynamic core (C1: the migrated temporal anchor; C2 adds the timeline) ── */}
      {hasElectorate && (
        <Card data-testid="campaign-dynamics-core">
          <CardHeader>
            <CardTitle className="text-base">🎬 Trajectoire de campagne</CardTitle>
          </CardHeader>
          <CardContent>
            <React.Suspense fallback={<AnchorFallback />}>
              <CampaignAnchor />
            </React.Suspense>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CampaignDynamicsPage;
