import { lazy, type ComponentType, type LazyExoticComponent } from 'react';

// lazyWithPreload — React.lazy plus a `.preload()` that triggers the dynamic
// import early (e.g. on hover/focus of a Collapsible toggle), so the chunk is
// already downloaded by the time the user opens the panel. Same lazy/Suspense
// semantics as React.lazy — the component still only MOUNTS when rendered, so the
// playground's "nothing computes at first paint" invariant is unchanged; preload
// only warms the network/parse cache.

// Mirrors React.lazy's own generic constraint (ComponentType<any>) so any panel
// shape is accepted regardless of its props.
type AnyComponent = ComponentType<any>;

export type PreloadableComponent<T extends AnyComponent> = LazyExoticComponent<T> & {
  preload: () => Promise<{ default: T }>;
};

export function lazyWithPreload<T extends AnyComponent>(
  factory: () => Promise<{ default: T }>
): PreloadableComponent<T> {
  const Component = lazy(factory) as PreloadableComponent<T>;
  Component.preload = factory;
  return Component;
}
