import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import BehavioralRealismAnchor from '../BehavioralRealismAnchor';

describe('BehavioralRealismAnchor (C4)', () => {
  it('mounts only the collapsible toggles — panels stay lazy until opened', () => {
    render(<BehavioralRealismAnchor />);
    for (const id of [
      'breal-biases',
      'breal-shyvoter',
      'breal-overload',
      'breal-compulsory',
      'breal-demographic',
      'breal-affective',
    ]) {
      expect(screen.getByTestId(`${id}-toggle`)).toBeInTheDocument();
    }
    // Form-lock: no heavy panel mounted (every Leaf is collapsed).
    expect(screen.queryByTestId('leaf-skeleton')).not.toBeInTheDocument();
  });
});
