import { POINT_RADIUS, drawScene, type DrawContext } from './drawScene';
import { MAP_COLORS, type MapPoint, type Scene } from './mapScene';

/** A 2D context that records what is drawn. */
function recorder() {
  const calls: string[] = [];
  const ctx = {
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    setTransform: (...a: number[]) => calls.push(`setTransform(${a.join(',')})`),
    clearRect: (...a: number[]) => calls.push(`clearRect(${a.join(',')})`),
    beginPath: () => calls.push('beginPath'),
    arc: (x: number, y: number, r: number) => calls.push(`arc(${x},${y},${r})`),
    rect: (...a: number[]) => calls.push(`rect(${a.join(',')})`),
    moveTo: () => calls.push('moveTo'),
    lineTo: () => calls.push('lineTo'),
    closePath: () => calls.push('closePath'),
    fill: () => calls.push(`fill(${ctx.fillStyle})`),
    stroke: () => calls.push(`stroke(${ctx.strokeStyle},${ctx.lineWidth})`),
  };
  return { ctx: ctx as unknown as DrawContext, calls };
}

const point = (id: number, shape: MapPoint['shape']): MapPoint => ({
  id,
  x: 10 * id,
  y: 5,
  shape,
  color: 'green',
  legend: 'x',
});

const scene = (points: MapPoint[]): Scene => ({
  width: 200,
  height: 100,
  points,
  legend: [],
  parties: [],
  president: null,
  project: () => [0, 0],
});

describe('drawScene', () => {
  it('clears at the device pixel ratio and draws each shape, outlines stroked and the rest filled', () => {
    const { ctx, calls } = recorder();
    drawScene(
      ctx,
      scene([
        point(1, 'circle'),
        point(2, 'ring'),
        point(3, 'square'),
        point(4, 'triangle'),
        point(5, 'diamond'),
        point(6, 'cross'),
      ]),
      2
    );
    const green = MAP_COLORS.green;
    expect(calls.slice(0, 2)).toEqual(['setTransform(2,0,0,2,0,0)', 'clearRect(0,0,200,100)']);
    expect(calls.slice(2)).toEqual([
      'beginPath',
      `arc(10,5,${POINT_RADIUS})`,
      `fill(${green})`,
      'beginPath',
      `arc(20,5,${POINT_RADIUS})`,
      `stroke(${green},1.5)`,
      'beginPath',
      `rect(${30 - POINT_RADIUS},${5 - POINT_RADIUS},${2 * POINT_RADIUS},${2 * POINT_RADIUS})`,
      `fill(${green})`,
      'beginPath',
      'moveTo',
      'lineTo',
      'lineTo',
      'closePath',
      `fill(${green})`,
      'beginPath',
      'moveTo',
      'lineTo',
      'lineTo',
      'lineTo',
      'closePath',
      `fill(${green})`,
      'beginPath',
      'moveTo',
      'lineTo',
      'moveTo',
      'lineTo',
      `stroke(${green},1.5)`,
    ]);
  });
});
