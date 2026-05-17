import { buildVoronoiPaths } from './voronoiRegions';

// Simple domainToSvg for tests: maps [-1,1] → [40, 440] on a 480px canvas
const SVG_W   = 480;
const SVG_H   = 480;
const MARGIN  = 40;
const PLOT_WH = SVG_W - 2 * MARGIN; // 400

function domainToSvg(v: number, axis: 'x' | 'y'): number {
  if (axis === 'x') return MARGIN + ((v + 1) / 2) * PLOT_WH;
  return MARGIN + ((1 - v) / 2) * PLOT_WH;  // Y flipped
}

describe('buildVoronoiPaths', () => {
  it('returns empty array for fewer than 2 candidates', () => {
    expect(buildVoronoiPaths([], SVG_W, SVG_H, domainToSvg)).toHaveLength(0);
    expect(buildVoronoiPaths(
      [{ x: 0, y: 0, name: 'Solo' }], SVG_W, SVG_H, domainToSvg
    )).toHaveLength(0);
  });

  it('returns one path per candidate', () => {
    const candidates = [
      { x: -0.5, y: -0.3, name: 'Alice' },
      { x:  0.5, y:  0.3, name: 'Bob'   },
      { x:  0.0, y: -0.5, name: 'Carol' },
    ];
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg);
    expect(paths).toHaveLength(3);
  });

  it('candidate names are preserved in output', () => {
    const candidates = [
      { x: -0.5, y: 0, name: 'Alice' },
      { x:  0.5, y: 0, name: 'Bob'   },
      { x:  0.0, y: 0.5, name: 'Carol' },
    ];
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg);
    const names = paths.map((p) => p.name);
    expect(names).toContain('Alice');
    expect(names).toContain('Bob');
    expect(names).toContain('Carol');
  });

  it('all non-empty paths start with "M" (valid SVG path)', () => {
    const candidates = [
      { x: -0.6, y: -0.3, name: 'Alice' },
      { x:  0.6, y:  0.3, name: 'Bob'   },
      { x:  0.0, y:  0.5, name: 'Carol' },
    ];
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg);
    for (const p of paths) {
      if (p.path.length > 0) {
        expect(p.path).toMatch(/^M/);
      }
    }
  });

  it('works with exactly 2 candidates', () => {
    const candidates = [
      { x: -0.5, y: 0, name: 'Alice' },
      { x:  0.5, y: 0, name: 'Bob'   },
    ];
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg);
    expect(paths).toHaveLength(2);
  });

  it('uses custom margin when provided', () => {
    const candidates = [
      { x: -0.5, y: 0, name: 'Alice' },
      { x:  0.5, y: 0, name: 'Bob'   },
    ];
    // Should not throw with custom margin
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg, 60);
    expect(paths).toHaveLength(2);
  });

  it('handles collinear points gracefully (no crash)', () => {
    // Three candidates on the same horizontal line — may produce degenerate Voronoi
    const candidates = [
      { x: -0.5, y: 0, name: 'Alice' },
      { x:  0.0, y: 0, name: 'Bob'   },
      { x:  0.5, y: 0, name: 'Carol' },
    ];
    expect(() =>
      buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg)
    ).not.toThrow();
    const paths = buildVoronoiPaths(candidates, SVG_W, SVG_H, domainToSvg);
    expect(paths).toHaveLength(3);
  });
});
