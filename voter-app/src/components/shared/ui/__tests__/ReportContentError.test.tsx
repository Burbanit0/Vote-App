import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import ReportContentError from '../ReportContentError';

describe('ReportContentError', () => {
  it('opens the content-error issue form with the place filled in', () => {
    render(<ReportContentError where="story:five/irv" />);
    const link = screen.getByTestId('report-content-error');
    const url = new URL(link.getAttribute('href')!);
    expect(url.origin + url.pathname).toBe('https://github.com/Burbanit0/Vote-App/issues/new');
    // The template file and the "where" field id must match .github/ISSUE_TEMPLATE.
    expect(url.searchParams.get('template')).toBe('content-error.yml');
    expect(url.searchParams.get('where')).toBe('story:five/irv');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(link).toHaveTextContent('Report a content error');
  });

  it('points at a form that exists and has a "where" field', () => {
    const form = readFileSync(
      resolve(__dirname, '../../../../../../.github/ISSUE_TEMPLATE/content-error.yml'),
      'utf8'
    );
    expect(form).toContain('    id: where\n');
  });
});
