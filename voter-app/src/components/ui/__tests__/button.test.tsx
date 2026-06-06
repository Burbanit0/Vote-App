import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button } from '../button';

describe('Button (shadcn/ui)', () => {
  it('renders a button with default variant classes', () => {
    render(<Button>Click</Button>);
    const btn = screen.getByRole('button', { name: 'Click' });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain('bg-primary');
    expect(btn.className).toContain('inline-flex');
  });

  it('applies the chosen variant + size', () => {
    render(
      <Button variant="outline" size="sm">
        Outline
      </Button>
    );
    const btn = screen.getByRole('button', { name: 'Outline' });
    expect(btn.className).toContain('border-input');
    expect(btn.className).toContain('h-8');
  });

  it('merges custom className (tailwind-merge wins last)', () => {
    render(<Button className="bg-destructive">X</Button>);
    const btn = screen.getByRole('button', { name: 'X' });
    // tailwind-merge resolves the base bg-* conflict to the override (the
    // hover:bg-primary/90 variant legitimately stays — different property).
    expect(btn.className).toContain('bg-destructive');
    expect(btn.className).not.toMatch(/(?:^|\s)bg-primary(?:\s|$)/);
  });

  it('renders as a child element when asChild is set', () => {
    render(
      <Button asChild>
        <a href="/x">Link</a>
      </Button>
    );
    const link = screen.getByRole('link', { name: 'Link' });
    expect(link).toBeInTheDocument();
    expect(link.className).toContain('inline-flex');
  });
});
