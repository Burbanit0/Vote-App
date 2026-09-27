import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import '@testing-library/jest-dom';
import LexiquePanel from '../LexiquePanel';

// Tests run in English (jsdom) → assert EN glossary copy.

const renderPanel = () =>
  render(
    <MemoryRouter>
      <LexiquePanel />
    </MemoryRouter>
  );

describe('LexiquePanel', () => {
  it('lists the glossary with a see-in-action link per term that has one', () => {
    renderPanel();
    expect(screen.getByTestId('lexique-panel')).toHaveTextContent('Condorcet winner');
    expect(screen.getByTestId('lexique-panel')).toHaveTextContent('Spoiler effect');
    // Approval → the France 2017 real-election panel.
    expect(screen.getByTestId('lexique-see-approval')).toHaveAttribute(
      'href',
      '/laboratoire?exp=res-real-election'
    );
  });

  it('search filters the list', () => {
    renderPanel();
    fireEvent.change(screen.getByTestId('lexique-search'), { target: { value: 'spoiler' } });
    const panel = screen.getByTestId('lexique-panel');
    expect(panel).toHaveTextContent('Spoiler effect');
    expect(panel).not.toHaveTextContent('Condorcet winner');
  });

  it('shows an empty state when nothing matches', () => {
    renderPanel();
    fireEvent.change(screen.getByTestId('lexique-search'), { target: { value: 'zzzzz' } });
    expect(screen.getByTestId('lexique-panel')).toHaveTextContent('No term matches.');
  });
});
