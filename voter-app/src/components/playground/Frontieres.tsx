import React from 'react';
import { usePlaygroundCtx } from './PlaygroundController';
import { AnchorFallback } from './playgroundFields';
import Collapsible from './Collapsible';

const MechanismsAnchor = React.lazy(() => import('./anchors/MechanismsAnchor'));
const AnalysisAnchor = React.lazy(() => import('./anchors/AnalysisAnchor'));
const TheoryAnchor = React.lazy(() => import('./anchors/TheoryAnchor'));
const SystemsAnchor = React.lazy(() => import('./anchors/SystemsAnchor'));
const ResultsAnchor = React.lazy(() => import('./anchors/ResultsAnchor'));

// Frontières — the deep, optional explorations (a moment further out). Full-width
// below the instrument, lazy + collapsed so first paint mounts none of them.
const Frontieres: React.FC = () => {
  const { mode } = usePlaygroundCtx();
  return (
    <>
      {mode === 'leader' && (
        <div className="mt-4">
          <Collapsible
            title="⚙️ Autres procédures de décision"
            subtitle="11 mécanismes (jury, sortition, délégation…)"
            testid="anchor-mechanisms"
          >
            <React.Suspense fallback={<AnchorFallback />}>
              <MechanismsAnchor />
            </React.Suspense>
          </Collapsible>
        </div>
      )}
      {mode === 'parliament' && (
        <div className="mt-4">
          <Collapsible
            title="🔬 Systèmes & circonscriptions"
            subtitle="7 vues (coalitions, districts, gerrymander…)"
            testid="anchor-systems"
          >
            <React.Suspense fallback={<AnchorFallback />}>
              <SystemsAnchor />
            </React.Suspense>
          </Collapsible>
        </div>
      )}
      <div className="mt-4">
        <Collapsible
          title="📋 Résultats complets (dépouillement)"
          subtitle="toutes les méthodes · animation"
          testid="anchor-results"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <ResultsAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
      <div className="mt-4">
        <Collapsible
          title="🔬 Analyse approfondie du résultat courant"
          subtitle="distributions · regret · manipulabilité"
          testid="anchor-analysis"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <AnalysisAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
      <div className="mt-4">
        <Collapsible
          title="🔬 Théorie & paradoxes du choix social"
          subtitle="Sen · jugements · McKelvey · pouvoir · recul démocratique…"
          testid="anchor-theory"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <TheoryAnchor />
          </React.Suspense>
        </Collapsible>
      </div>
    </>
  );
};

export default Frontieres;
