// hemicycleGeometry.ts — the parliament-semicircle math, shared by every panel
// that draws one (GerrymanderMap, STVPanel, MultiwinnerCompare). Each panel
// still owns its own size, styling, and extra chrome (a threshold line, a JR
// badge, a testid) — only the angle arithmetic was ever byte-identical between
// them, so only that part is shared.

export interface HemicycleSegment {
  name: string;
  a1: number;
  a2: number;
}

/** Party wedges around a semicircle, left to right, each sized by its seat
 * share. Angles run from π (left) down to 0 (right). */
export function hemicycleSegments(
  seats: Record<string, number>,
  names: string[],
  total: number
): HemicycleSegment[] {
  const parties = names.filter((n) => (seats[n] ?? 0) > 0);
  let cum = Math.PI;
  return parties.map((n) => {
    const span = ((seats[n] ?? 0) / total) * Math.PI;
    const s = { name: n, a1: cum, a2: cum + span };
    cum += span;
    return s;
  });
}

/** Point at radius `r`, angle `a`, on a semicircle centred at (cx, cy). */
export function hemicycleArc(cx: number, cy: number, r: number, a: number): [number, number] {
  return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
}

/** SVG path `d` for the ring-segment wedge between radii r1/r2 and angles a1/a2. */
export function hemicyclePath(
  cx: number,
  cy: number,
  r1: number,
  r2: number,
  a1: number,
  a2: number
): string {
  const [x1, y1] = hemicycleArc(cx, cy, r1, a1);
  const [x2, y2] = hemicycleArc(cx, cy, r2, a1);
  const [x3, y3] = hemicycleArc(cx, cy, r2, a2);
  const [x4, y4] = hemicycleArc(cx, cy, r1, a2);
  const la = a2 - a1 > Math.PI ? 1 : 0;
  return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
}
