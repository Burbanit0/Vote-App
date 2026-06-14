import { describe, it, expect } from 'vitest';
import { errorMessage } from '../errorMessage';

describe('errorMessage', () => {
  it('prefers a backend response.data.error', () => {
    const e = { response: { data: { error: 'Backend says no' } }, message: 'ignored' };
    expect(errorMessage(e, 'fallback')).toBe('Backend says no');
  });

  it('falls back to Error.message', () => {
    expect(errorMessage(new Error('boom'), 'fallback')).toBe('boom');
  });

  it('uses the fallback for opaque / empty errors', () => {
    expect(errorMessage('a string', 'fallback')).toBe('fallback');
    expect(errorMessage(null, 'fallback')).toBe('fallback');
    expect(errorMessage({ response: { data: {} } }, 'fallback')).toBe('fallback');
  });
});
