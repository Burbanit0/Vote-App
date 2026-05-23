import React from 'react';
import { render, screen } from '@testing-library/react';
import PageContainer from '../PageContainer';
import { LAYOUT } from '../tokens';

describe('PageContainer', () => {
  it('defaults to medium width', () => {
    render(
      <PageContainer data-testid="pc">
        <span>content</span>
      </PageContainer>
    );
    const el = screen.getByTestId('pc');
    expect(el.style.maxWidth).toBe(`${LAYOUT.pageMedium}px`);
  });

  it.each([
    ['narrow', LAYOUT.pageNarrow],
    ['medium', LAYOUT.pageMedium],
    ['wide',   LAYOUT.pageWide],
    ['full',   LAYOUT.pageFull],
  ] as const)('applies the %s variant width (%i)', (variant, expected) => {
    render(
      <PageContainer variant={variant} data-testid="pc">
        <span>x</span>
      </PageContainer>
    );
    expect(screen.getByTestId('pc').style.maxWidth).toBe(`${expected}px`);
  });

  it('renders children', () => {
    render(
      <PageContainer>
        <span data-testid="child">hello</span>
      </PageContainer>
    );
    expect(screen.getByTestId('child')).toHaveTextContent('hello');
  });

  it('merges custom className and style', () => {
    render(
      <PageContainer className="custom-cls" style={{ background: 'red' }} data-testid="pc">
        <span>x</span>
      </PageContainer>
    );
    const el = screen.getByTestId('pc');
    expect(el.className).toContain('custom-cls');
    expect(el.style.background).toBe('red');
  });

  it('uses the configured padding class (default py-4)', () => {
    render(<PageContainer data-testid="pc"><span>x</span></PageContainer>);
    expect(screen.getByTestId('pc').className).toContain('py-4');
  });

  it('honours a custom padding override', () => {
    render(<PageContainer padding="py-2" data-testid="pc"><span>x</span></PageContainer>);
    expect(screen.getByTestId('pc').className).toContain('py-2');
  });
});
