import { messageOf } from './errors';

describe('messageOf', () => {
  it('reads the API’s detail, and anything else as text', () => {
    expect(messageOf({ detail: 'run not found' })).toBe('run not found');
    expect(messageOf('unreachable')).toBe('unreachable');
    expect(messageOf(null)).toBe('null');
  });
});
