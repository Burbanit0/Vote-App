import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import InternationalRegimesPage from './InternationalRegimesPage';
import regimes, {
  BlankVoteRegime,
  sortByBlankRate,
  filterByImpact,
} from '../data/blankVoteRegimes';

vi.mock('../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));

// ── Dataset integrity ─────────────────────────────────────────────────────────

describe('blankVoteRegimes dataset', () => {
  const REQUIRED_FIELDS: (keyof BlankVoteRegime)[] = [
    'country',
    'flag',
    'legal_status',
    'description',
    'blank_rate_typical',
    'impact_on_result',
    'source',
    'lat',
    'lon',
  ];

  it('has at least 15 entries', () => {
    expect(regimes.length).toBeGreaterThanOrEqual(15);
  });

  it('every entry has all required fields', () => {
    regimes.forEach((r) => {
      REQUIRED_FIELDS.forEach((field) => {
        expect(r[field]).toBeDefined();
        expect(r[field]).not.toBeNull();
        if (typeof r[field] === 'string') {
          expect((r[field] as string).length).toBeGreaterThan(0);
        }
      });
    });
  });

  it('every legal_status is a valid value', () => {
    const valid = new Set([
      'counted_separate',
      'symbolic',
      'competitive',
      'threshold',
      'merged_invalid',
    ]);
    regimes.forEach((r) => {
      expect(valid.has(r.legal_status)).toBe(true);
    });
  });

  it('blank_rate_typical is between 0 and 100 for all entries', () => {
    regimes.forEach((r) => {
      expect(r.blank_rate_typical).toBeGreaterThanOrEqual(0);
      expect(r.blank_rate_typical).toBeLessThanOrEqual(100);
    });
  });

  it('lat/lon coordinates are within valid geographic ranges', () => {
    regimes.forEach((r) => {
      expect(r.lat).toBeGreaterThanOrEqual(-90);
      expect(r.lat).toBeLessThanOrEqual(90);
      expect(r.lon).toBeGreaterThanOrEqual(-180);
      expect(r.lon).toBeLessThanOrEqual(180);
    });
  });

  it('contains France, Colombie, Uruguay (key reference countries)', () => {
    const countries = regimes.map((r) => r.country);
    expect(countries).toContain('France');
    expect(countries).toContain('Colombie');
    expect(countries).toContain('Uruguay');
  });

  it('France has counted_separate status since 2014', () => {
    const france = regimes.find((r) => r.country === 'France');
    expect(france).toBeDefined();
    expect(france!.legal_status).toBe('counted_separate');
    expect(france!.since_year).toBe(2014);
    expect(france!.impact_on_result).toBe(false);
  });

  it('Colombie and Uruguay have impact_on_result = true', () => {
    const colombia = regimes.find((r) => r.country === 'Colombie');
    const uruguay  = regimes.find((r) => r.country === 'Uruguay');
    expect(colombia?.impact_on_result).toBe(true);
    expect(uruguay?.impact_on_result).toBe(true);
  });

  it('all impact=true countries have competitive or threshold status', () => {
    regimes
      .filter((r) => r.impact_on_result)
      .forEach((r) => {
        expect(['competitive', 'threshold']).toContain(r.legal_status);
      });
  });

  it('has non-empty source for every entry', () => {
    regimes.forEach((r) => {
      expect(r.source.trim().length).toBeGreaterThan(5);
    });
  });
});

// ── sortByBlankRate ───────────────────────────────────────────────────────────

describe('sortByBlankRate', () => {
  it('sorts descending by default (sortAsc=false)', () => {
    const sorted = sortByBlankRate(regimes, false);
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i].blank_rate_typical).toBeLessThanOrEqual(
        sorted[i - 1].blank_rate_typical,
      );
    }
  });

  it('sorts ascending when sortAsc=true', () => {
    const sorted = sortByBlankRate(regimes, true);
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i].blank_rate_typical).toBeGreaterThanOrEqual(
        sorted[i - 1].blank_rate_typical,
      );
    }
  });

  it('does not mutate the original array', () => {
    const original = [...regimes];
    sortByBlankRate(regimes, true);
    expect(regimes.map((r) => r.country)).toEqual(original.map((r) => r.country));
  });

  it('first entry in ascending sort has lowest rate', () => {
    const sorted = sortByBlankRate(regimes, true);
    const minRate = Math.min(...regimes.map((r) => r.blank_rate_typical));
    expect(sorted[0].blank_rate_typical).toBe(minRate);
  });

  it('first entry in descending sort has highest rate', () => {
    const sorted = sortByBlankRate(regimes, false);
    const maxRate = Math.max(...regimes.map((r) => r.blank_rate_typical));
    expect(sorted[0].blank_rate_typical).toBe(maxRate);
  });
});

// ── filterByImpact ────────────────────────────────────────────────────────────

describe('filterByImpact', () => {
  it('returns only entries where impact_on_result = true', () => {
    const filtered = filterByImpact(regimes);
    expect(filtered.length).toBeGreaterThan(0);
    filtered.forEach((r) => {
      expect(r.impact_on_result).toBe(true);
    });
  });

  it('filters out entries with impact_on_result = false', () => {
    const filtered = filterByImpact(regimes);
    const noImpact = regimes.filter((r) => !r.impact_on_result);
    noImpact.forEach((r) => {
      expect(filtered.map((f) => f.country)).not.toContain(r.country);
    });
  });

  it('result count is smaller than total', () => {
    const filtered = filterByImpact(regimes);
    expect(filtered.length).toBeLessThan(regimes.length);
  });

  it('includes Colombie and Uruguay', () => {
    const filtered = filterByImpact(regimes);
    const countries = filtered.map((r) => r.country);
    expect(countries).toContain('Colombie');
    expect(countries).toContain('Uruguay');
  });
});

// ── InternationalRegimesPage rendering ───────────────────────────────────────

describe('InternationalRegimesPage', () => {
  it('renders without crash', () => {
    render(<InternationalRegimesPage />);
    expect(screen.getByRole('img', { name: /carte/i })).toBeInTheDocument();
  });

  it('shows page title', () => {
    render(<InternationalRegimesPage />);
    expect(screen.getByText(/Régimes internationaux/i)).toBeInTheDocument();
  });

  it('shows all countries in the table', () => {
    render(<InternationalRegimesPage />);
    // France is always visible
    expect(screen.getAllByText('France').length).toBeGreaterThanOrEqual(1);
  });

  it('impact filter toggle reduces the table rows', () => {
    render(<InternationalRegimesPage />);
    const impactBtn = screen.getByRole('button', { name: /afficher seulement/i });

    // Count rows before filtering
    const rowsBefore = screen.getAllByText(/⚠️ Oui|Non/).length;

    fireEvent.click(impactBtn);

    // After filtering, only impact countries remain
    const impactCount = filterByImpact(regimes).length;
    const rowsAfter   = screen.getAllByText(/⚠️ Oui/).length;
    expect(rowsAfter).toBe(impactCount);
    expect(rowsAfter).toBeLessThan(rowsBefore);
  });

  it('sort toggle button changes sort order', () => {
    render(<InternationalRegimesPage />);
    const sortBtn = screen.getByRole('button', { name: /trier/i });

    // Initially sorted descending (↓)
    expect(sortBtn.textContent).toContain('↓');

    fireEvent.click(sortBtn);

    // After click: ascending (↑)
    expect(sortBtn.textContent).toContain('↑');
  });

  it('summary conclusion mentions correct counts', () => {
    render(<InternationalRegimesPage />);
    const impactCount = filterByImpact(regimes).length;
    // The conclusion says "dans X pays sur Y"
    const conclusionText = screen.getByText(/Synthèse/i)
      .closest('div')?.textContent ?? '';
    expect(conclusionText).toContain(String(impactCount));
    expect(conclusionText).toContain(String(regimes.length));
  });
});
