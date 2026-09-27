/**
 * lib/polity/drawScene.ts — draws a population map scene on a 2D context, pure
 * (ADR-013).
 *
 * It takes any object with the few CanvasRenderingContext2D members it uses, so
 * the tests hand it a recording context and read back what was drawn, instead
 * of comparing pixels. The real rasterization is left to the pinned-image
 * screenshot baselines.
 */
import { MAP_COLORS, type MapPoint, type Scene } from './mapScene';

export type DrawContext = Pick<
  CanvasRenderingContext2D,
  | 'setTransform'
  | 'clearRect'
  | 'beginPath'
  | 'arc'
  | 'rect'
  | 'moveTo'
  | 'lineTo'
  | 'closePath'
  | 'fill'
  | 'stroke'
> & {
  fillStyle: string | CanvasGradient | CanvasPattern;
  strokeStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
};

export const POINT_RADIUS = 3.5;

function tracePoint(ctx: DrawContext, point: MapPoint, r: number): void {
  const { x, y } = point;
  switch (point.shape) {
    case 'circle':
    case 'ring':
      ctx.arc(x, y, r, 0, Math.PI * 2);
      return;
    case 'square':
      ctx.rect(x - r, y - r, 2 * r, 2 * r);
      return;
    case 'triangle':
      ctx.moveTo(x, y - r * 1.2);
      ctx.lineTo(x + r * 1.1, y + r * 0.9);
      ctx.lineTo(x - r * 1.1, y + r * 0.9);
      ctx.closePath();
      return;
    case 'diamond':
      ctx.moveTo(x, y - r * 1.3);
      ctx.lineTo(x + r * 1.3, y);
      ctx.lineTo(x, y + r * 1.3);
      ctx.lineTo(x - r * 1.3, y);
      ctx.closePath();
      return;
    case 'cross':
      ctx.moveTo(x - r, y - r);
      ctx.lineTo(x + r, y + r);
      ctx.moveTo(x + r, y - r);
      ctx.lineTo(x - r, y + r);
      return;
  }
}

/**
 * Clears the canvas at its device-pixel size and draws every citizen. Outline
 * shapes (ring, cross) are stroked; the others are filled.
 */
export function drawScene(ctx: DrawContext, scene: Scene, pixelRatio: number): void {
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  ctx.clearRect(0, 0, scene.width, scene.height);
  for (const point of scene.points) {
    const color = MAP_COLORS[point.color];
    ctx.beginPath();
    tracePoint(ctx, point, POINT_RADIUS);
    if (point.shape === 'ring' || point.shape === 'cross') {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      ctx.fillStyle = color;
      ctx.fill();
    }
  }
}
