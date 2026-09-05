import { describe, it, expect } from 'vitest';
import { numericTooltipFormatter } from './rechartsFormatters';

describe('numericTooltipFormatter', () => {
  it('coerces a numeric value through to the wrapped formatter', () => {
    const fmt = numericTooltipFormatter((v) => `${v}%`);
    expect(fmt(42, 'Support')).toBe('42%');
  });

  it('coerces the name through as a string', () => {
    const fmt = numericTooltipFormatter((v, name) => [`${v}`, name]);
    expect(fmt(3, 'Series A')).toEqual(['3', 'Series A']);
  });

  it('falls back to an empty name when recharts omits it', () => {
    const fmt = numericTooltipFormatter((v, name) => [`${v}`, name]);
    expect(fmt(1, undefined)).toEqual(['1', '']);
  });

  it('is the safe no-op recharts 3.x actually needs: a defined numeric value passes through unchanged', () => {
    const fmt = numericTooltipFormatter((v) => v.toFixed(2));
    expect(fmt(1.5, 'x')).toBe('1.50');
  });
});
