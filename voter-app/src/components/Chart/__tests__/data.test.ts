import { data } from '../data';

describe('chart data', () => {
  it('exports an array with 2 candidates', () => {
    expect(Array.isArray(data)).toBe(true);
    expect(data).toHaveLength(2);
  });

  it('each entry has x, y, size and group', () => {
    data.forEach((d) => {
      expect(d).toHaveProperty('x');
      expect(d).toHaveProperty('y');
      expect(d).toHaveProperty('size');
      expect(d).toHaveProperty('group');
    });
  });
});
