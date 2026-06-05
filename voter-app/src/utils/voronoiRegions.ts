/**
 * voronoiRegions.ts — Compute SVG Voronoi paths from candidate positions.
 *
 * Uses d3-delaunay to partition the SVG canvas into one region per candidate.
 * Each region contains all points closer to that candidate than to any other.
 */
import { Delaunay } from 'd3-delaunay';

export interface VoronoiRegion {
  name: string;
  path: string;
}

/**
 * Build Voronoi SVG paths for a set of candidates.
 *
 * @param candidates - Array of candidates with domain coords (x,y ∈ [-1,1]) and names.
 * @param svgWidth   - Total SVG width in pixels.
 * @param svgHeight  - Total SVG height in pixels.
 * @param domainToSvg - Function converting a domain value to SVG pixels for one axis.
 * @param margin     - Canvas margin in pixels (defaults to 40).
 * @returns One { name, path } per candidate. Path is a valid SVG "d" attribute string.
 */
export function buildVoronoiPaths(
  candidates: { x: number; y: number; name: string }[],
  svgWidth: number,
  svgHeight: number,
  domainToSvg: (v: number, axis: 'x' | 'y') => number,
  margin = 40
): VoronoiRegion[] {
  if (candidates.length < 2) return [];

  // Convert domain coordinates to SVG pixel positions
  const svgPoints: [number, number][] = candidates.map((c) => [
    domainToSvg(c.x, 'x'),
    domainToSvg(c.y, 'y'),
  ]);

  // Bounds: clamp Voronoi cells to the canvas area (inside the margin)
  const bounds: [number, number, number, number] = [
    margin,
    margin,
    svgWidth - margin,
    svgHeight - margin,
  ];

  try {
    const delaunay = Delaunay.from(svgPoints);
    const voronoi = delaunay.voronoi(bounds);

    return candidates.map((c, i) => ({
      name: c.name,
      path: voronoi.renderCell(i) ?? '',
    }));
  } catch {
    // Degenerate case (collinear points, etc.) — return empty paths
    return candidates.map((c) => ({ name: c.name, path: '' }));
  }
}
