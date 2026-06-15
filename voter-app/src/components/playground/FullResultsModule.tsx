import React from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Spinner } from '@/components/ui/spinner';
import { useElection } from '../../stores/useElectionStore';
import { simulateElection, type ElectionResult } from '../../services/electionApi';
import ResultsMethodTable from '../shared/ResultsMethodTable';
import ElectionInsightPanel from '../shared/ElectionInsightPanel';
import HistoricalReferencePanel from '../shared/HistoricalReferencePanel';

// FullResultsModule — the Lab's core "results" view absorbed into the playground:
// run a full simulation on the shared electorate, then show the per-method winner
// table + the narrative insight + the historical reference. On-demand (run button).

const FullResultsModule: React.FC = () => {
  const { config } = useElection();
  const [result, setResult] = React.useState<ElectionResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(false);

  const run = async () => {
    setLoading(true);
    setError(false);
    try {
      setResult(await simulateElection(config));
    } catch {
      setError(true);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="full-results-module" className="flex flex-col gap-3">
      <p className="text-[0.7rem] text-muted-foreground/80">
        La table complète des méthodes (vainqueur · regret bayésien · conformité Condorcet), plus la
        lecture narrative et la référence historique — sur l’électorat partagé.
      </p>
      <Button
        data-testid="full-results-run"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={run}
        disabled={loading}
      >
        {loading ? (
          <>
            <Spinner size="sm" /> Simulation…
          </>
        ) : result ? (
          '↻ Re-simuler'
        ) : (
          '▶ Simuler toutes les méthodes'
        )}
      </Button>

      {error && <Alert variant="danger">Erreur lors de la simulation.</Alert>}

      {result && (
        <div className="flex flex-col gap-4">
          <ResultsMethodTable result={result} />
          <ElectionInsightPanel result={result} />
          <HistoricalReferencePanel result={result} />
        </div>
      )}
    </div>
  );
};

export default FullResultsModule;
