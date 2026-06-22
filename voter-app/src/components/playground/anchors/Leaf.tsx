import React from 'react';
import Collapsible from '../Collapsible';

// Leaf — a collapsed sub-section that lazy-mounts its panel on open. Shared by
// every contextual anchor so the playground's perf invariant holds uniformly:
// the Collapsible only renders children when open, and each panel passed in is
// lazy, so nothing computes or fetches until the user asks.
//
// Perf (Phase 0): pass `prefetch` (a lazy component's `.preload`) so hovering the
// toggle warms the chunk before the click; the fallback is a sized skeleton so the
// panel's appearance doesn't shift layout.

const Skeleton: React.FC = () => (
  <div className="animate-pulse space-y-2" data-testid="leaf-skeleton" aria-hidden>
    <div className="h-4 w-1/3 rounded bg-muted" />
    <div className="h-24 rounded bg-muted" />
    <div className="h-4 w-2/3 rounded bg-muted" />
  </div>
);

const Leaf: React.FC<{
  title: string;
  testid: string;
  /** A `lazyWithPreload(...).preload` to warm the chunk on toggle hover/focus. */
  prefetch?: () => void;
  children: React.ReactNode;
}> = ({ title, testid, prefetch, children }) => (
  <Collapsible title={title} testid={testid} onPrefetch={prefetch}>
    <React.Suspense fallback={<Skeleton />}>{children}</React.Suspense>
  </Collapsible>
);

export default Leaf;
