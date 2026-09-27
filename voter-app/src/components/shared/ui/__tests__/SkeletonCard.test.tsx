import React from 'react';
import { render, screen } from '@testing-library/react';
import SkeletonCard from '../SkeletonCard';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

describe('SkeletonCard', () => {
  it('announces itself as a loading status', () => {
    render(<SkeletonCard />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'common.loading');
  });

  it('pulses, and stops pulsing when the viewer asks for reduced motion', () => {
    render(<SkeletonCard />);
    // The animation is Tailwind's, not an injected keyframe block: the class is
    // the whole implementation, so it is what there is to assert.
    expect(screen.getByRole('status')).toHaveClass('animate-pulse', 'motion-reduce:animate-none');
  });

  it('takes its size from the props and draws a header plus three lines', () => {
    const { container } = render(<SkeletonCard height={120} width="40%" />);
    const card = screen.getByRole('status');
    expect(card).toHaveStyle({ height: '120px', width: '40%' });
    // Four placeholder lines (header + 3) and the rule under the header, all
    // hidden from screen readers -- the status label above speaks for them.
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(4);
  });
});
