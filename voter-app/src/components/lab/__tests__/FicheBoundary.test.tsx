import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FicheBoundary from '../FicheBoundary';
import i18n from '../../../i18n';

const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
afterAll(() => errorSpy.mockRestore());

let broken = true;
const Boom: React.FC = () => {
  if (broken) throw new Error('boom');
  return <span data-testid="fiche-ok">ok</span>;
};

beforeEach(() => {
  broken = true;
});

describe('FicheBoundary', () => {
  it('renders the fiche untouched while it works', () => {
    broken = false;
    render(
      <FicheBoundary>
        <Boom />
      </FicheBoundary>
    );
    expect(screen.getByTestId('fiche-ok')).toBeInTheDocument();
    expect(screen.queryByTestId('fiche-error')).not.toBeInTheDocument();
  });

  it('a throwing fiche shows its own message and a retry, and only that', () => {
    render(
      <div>
        <span data-testid="sibling">rail</span>
        <FicheBoundary>
          <Boom />
        </FicheBoundary>
      </div>
    );
    expect(screen.getByTestId('fiche-error')).toHaveTextContent('This fiche hit an error');
    expect(screen.getByTestId('fiche-error-retry')).toHaveTextContent('Try again');
    expect(screen.getByTestId('sibling')).toBeInTheDocument();
    expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
  });

  it('retry remounts the fiche: it recovers once the cause is gone, and fails again if not', () => {
    render(
      <FicheBoundary>
        <Boom />
      </FicheBoundary>
    );
    fireEvent.click(screen.getByTestId('fiche-error-retry'));
    expect(screen.getByTestId('fiche-error')).toBeInTheDocument();
    broken = false;
    fireEvent.click(screen.getByTestId('fiche-error-retry'));
    expect(screen.getByTestId('fiche-ok')).toBeInTheDocument();
    expect(screen.queryByTestId('fiche-error')).not.toBeInTheDocument();
  });

  it('speaks French when the page does, with the same keys as English', async () => {
    const previous = i18n.language;
    await i18n.changeLanguage('fr');
    try {
      render(
        <FicheBoundary>
          <Boom />
        </FicheBoundary>
      );
      expect(screen.getByTestId('fiche-error')).toHaveTextContent(
        'Cette fiche a rencontré une erreur'
      );
      expect(screen.getByTestId('fiche-error-retry')).toHaveTextContent('Réessayer');
    } finally {
      await i18n.changeLanguage(previous);
    }
  });
});
