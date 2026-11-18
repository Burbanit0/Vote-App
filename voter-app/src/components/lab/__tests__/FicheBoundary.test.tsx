import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FicheBoundary from '../FicheBoundary';
import i18n from '../../../i18n';

const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
afterAll(() => errorSpy.mockRestore());

let broken = true;
let failure = new Error('boom');
const Boom: React.FC = () => {
  if (broken) throw failure;
  return <span data-testid="fiche-ok">ok</span>;
};

beforeEach(() => {
  broken = true;
  failure = new Error('boom');
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

  it('says what failed, so it can be reported', () => {
    render(
      <FicheBoundary>
        <Boom />
      </FicheBoundary>
    );
    expect(screen.getByTestId('fiche-error-detail')).toHaveTextContent('Error: boom');
  });

  it('a chunk that failed to load reloads the page on Retry: a remount would re-throw the cached rejection', () => {
    const reload = vi.fn();
    vi.stubGlobal('location', { ...window.location, reload });
    try {
      failure = new TypeError('Failed to fetch dynamically imported module: /assets/x.js');
      render(
        <FicheBoundary>
          <Boom />
        </FicheBoundary>
      );
      fireEvent.click(screen.getByTestId('fiche-error-retry'));
      expect(reload).toHaveBeenCalledTimes(1);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('any other error retries in place, without a reload', () => {
    const reload = vi.fn();
    vi.stubGlobal('location', { ...window.location, reload });
    try {
      render(
        <FicheBoundary>
          <Boom />
        </FicheBoundary>
      );
      broken = false;
      fireEvent.click(screen.getByTestId('fiche-error-retry'));
      expect(reload).not.toHaveBeenCalled();
      expect(screen.getByTestId('fiche-ok')).toBeInTheDocument();
    } finally {
      vi.unstubAllGlobals();
    }
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
