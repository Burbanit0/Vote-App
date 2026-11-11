import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HaloList } from '../card-hover-effect';
import { HeroHighlight, Highlight } from '../hero-highlight';
import { Spotlight } from '../spotlight-new';

const ITEMS = ['a', 'b'].map((key) => ({ key, node: <a href={`#${key}`}>{key}</a> }));

describe('HaloList', () => {
  it('shows the halo on the hovered item only, and clears it on leave', async () => {
    render(<HaloList as="ul" layoutId="t" items={ITEMS} />);
    expect(screen.queryByTestId('hover-halo')).toBeNull();

    fireEvent.mouseEnter(screen.getByText('b').closest('li')!);
    const halo = await screen.findByTestId('hover-halo');
    expect(halo.closest('li')).toHaveTextContent('b');

    fireEvent.mouseLeave(screen.getByRole('list'));
    await waitFor(() => expect(screen.queryByTestId('hover-halo')).toBeNull());
  });

  it('follows keyboard focus too', async () => {
    render(<HaloList as="ol" layoutId="t" items={ITEMS} />);
    fireEvent.focus(screen.getByText('a'));
    expect((await screen.findByTestId('hover-halo')).closest('li')).toHaveTextContent('a');

    fireEvent.blur(screen.getByText('a'));
    await waitFor(() => expect(screen.queryByTestId('hover-halo')).toBeNull());
  });
});

describe('HeroHighlight', () => {
  it('tracks the pointer in CSS variables, relative to the hero', () => {
    render(
      <HeroHighlight>
        <p>child</p>
      </HeroHighlight>
    );
    const hero = screen.getByTestId('hero-highlight');
    // jsdom lays nothing out: the rect is all zeros, so offset = client coords.
    fireEvent.mouseMove(hero, { clientX: 40, clientY: 12 });
    expect(hero.style.getPropertyValue('--hx')).toBe('40px');
    expect(hero.style.getPropertyValue('--hy')).toBe('12px');
    expect(screen.getByText('child')).toBeInTheDocument();
  });

  it('Highlight keeps its text and carries the sweep animation class', () => {
    render(<Highlight className="text-primary">phrase</Highlight>);
    expect(screen.getByText('phrase')).toHaveClass('highlight-sweep', 'text-primary');
  });
});

describe('Spotlight', () => {
  it('is decorative and drifts the two cones in opposite directions', () => {
    const { container } = render(<Spotlight />);
    const root = container.firstElementChild as HTMLElement;
    expect(root).toHaveAttribute('aria-hidden', 'true');
    const drifts = Array.from(root.querySelectorAll<HTMLElement>('.spotlight-drift')).map((el) =>
      el.style.getPropertyValue('--drift')
    );
    expect(drifts).toEqual(['100px', '-100px']);
  });
});
