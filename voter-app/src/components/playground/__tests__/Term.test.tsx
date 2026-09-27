import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import '@testing-library/jest-dom';
import Term from '../Term';

// Tests run in English (jsdom) → assert EN glossary copy.

const renderTerm = (id: string, label?: string) =>
  render(
    <MemoryRouter>
      <Term id={id}>{label}</Term>
    </MemoryRouter>
  );

describe('Term', () => {
  it('renders the word and, on click, a plain-language popover', () => {
    renderTerm('condorcet', 'Condorcet');
    expect(screen.getByText('Condorcet')).toBeInTheDocument();
    // Popover is closed until the ⓘ is clicked.
    expect(screen.queryByTestId('pop-term-condorcet')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('info-term-condorcet'));
    const pop = screen.getByTestId('pop-term-condorcet');
    expect(pop).toHaveTextContent('Condorcet winner');
    expect(pop).toHaveTextContent('one-on-one');
  });

  it('offers a "see it in action" deep-link to the demo', () => {
    renderTerm('condorcet', 'Condorcet');
    fireEvent.click(screen.getByTestId('info-term-condorcet'));
    // Condorcet → the "it depends who counts" story.
    expect(screen.getByTestId('term-see-condorcet')).toHaveAttribute(
      'href',
      '/playground?story=paradox'
    );
  });

  it('fails safe on an unknown id: renders the children untouched, no ⓘ', () => {
    renderTerm('not-a-real-term', 'plain text');
    expect(screen.getByText('plain text')).toBeInTheDocument();
    expect(screen.queryByTestId('info-term-not-a-real-term')).not.toBeInTheDocument();
  });
});
