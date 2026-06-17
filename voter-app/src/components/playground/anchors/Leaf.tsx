import React from 'react';
import Collapsible from '../Collapsible';

// Leaf — a collapsed sub-section that lazy-mounts its panel on open. Shared by
// every contextual anchor so the playground's perf invariant holds uniformly:
// the Collapsible only renders children when open, and each panel passed in is
// React.lazy, so nothing computes or fetches until the user asks.

const Fallback: React.FC = () => <p className="p-2 text-xs text-muted-foreground">Chargement…</p>;

const Leaf: React.FC<{ title: string; testid: string; children: React.ReactNode }> = ({
  title,
  testid,
  children,
}) => (
  <Collapsible title={title} testid={testid}>
    <React.Suspense fallback={<Fallback />}>{children}</React.Suspense>
  </Collapsible>
);

export default Leaf;
