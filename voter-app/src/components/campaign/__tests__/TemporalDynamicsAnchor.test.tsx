import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TemporalDynamicsAnchor from '../TemporalDynamicsAnchor';

describe('TemporalDynamicsAnchor (C3)', () => {
  it('mounts only the collapsible toggles — panels stay lazy until opened', () => {
    render(<TemporalDynamicsAnchor />);
    for (const id of [
      'tdyn-adaptive',
      'tdyn-replay',
      'tdyn-primary',
      'tdyn-cascade',
      'tdyn-fatigue',
    ]) {
      expect(screen.getByTestId(`${id}-toggle`)).toBeInTheDocument();
    }
    // Form-lock: no heavy panel is mounted (the lazy Suspense skeleton is absent
    // because every Leaf is collapsed).
    expect(screen.queryByTestId('leaf-skeleton')).not.toBeInTheDocument();
  });
});
