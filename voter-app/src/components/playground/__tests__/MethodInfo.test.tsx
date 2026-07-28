import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MethodInfo from '../MethodInfo';

describe('MethodInfo', () => {
  it('ships collapsed — only the ⓘ trigger, no content until clicked', () => {
    render(<MethodInfo method="irv" />);
    expect(screen.getByTestId('info-irv')).toBeInTheDocument();
    expect(screen.queryByTestId('pop-irv')).not.toBeInTheDocument();
  });

  it('reveals the method explanation on click', () => {
    render(<MethodInfo method="irv" />);
    fireEvent.click(screen.getByTestId('info-irv'));
    const pop = screen.getByTestId('pop-irv');
    expect(pop).toHaveTextContent(/Vote alternatif|Instant-runoff/);
    // The pedagogical fields are present.
    expect(pop).toHaveTextContent(/Principe|How/);
    expect(pop).toHaveTextContent(/Faille|Weakness/);
    // Phase 6: the everyday analogy ("comme dans la vie").
    expect(pop).toHaveTextContent(/Like real life|Comme dans la vie/);
    expect(pop).toHaveTextContent(/knockout game|jeu d’élimination/);
  });

  it('resolves backend aliases (star_voting → STAR, copeland → Condorcet)', () => {
    const { unmount } = render(<MethodInfo method="star_voting" />);
    fireEvent.click(screen.getByTestId('info-star_voting'));
    expect(screen.getByTestId('pop-star_voting')).toHaveTextContent(/STAR/);
    unmount();

    render(<MethodInfo method="copeland" />);
    fireEvent.click(screen.getByTestId('info-copeland'));
    expect(screen.getByTestId('pop-copeland')).toHaveTextContent(/Condorcet/);
  });

  it('covers parliament structures (pr/fptp/mmp)', () => {
    render(<MethodInfo method="fptp" />);
    fireEvent.click(screen.getByTestId('info-fptp'));
    expect(screen.getByTestId('pop-fptp')).toHaveTextContent(/Circonscriptions|Districts/);
  });

  it('renders nothing for an unknown method id (safe to drop anywhere)', () => {
    const { container } = render(<MethodInfo method="not_a_method" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('adds the live cycle note for the Condorcet family when no Condorcet winner exists', () => {
    render(<MethodInfo method="schulze" context={{ condorcetExists: false }} />);
    fireEvent.click(screen.getByTestId('info-schulze'));
    expect(screen.getByTestId('pop-schulze')).toHaveTextContent(
      /vainqueur de Condorcet|Condorcet winner/
    );
  });

  it('omits the cycle note when a Condorcet winner exists', () => {
    render(<MethodInfo method="schulze" context={{ condorcetExists: true }} />);
    fireEvent.click(screen.getByTestId('info-schulze'));
    expect(screen.getByTestId('pop-schulze')).not.toHaveTextContent(/⚡/);
  });
});
