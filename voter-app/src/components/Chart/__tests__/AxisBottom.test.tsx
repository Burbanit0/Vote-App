import { render, screen } from '@testing-library/react';
import * as d3 from 'd3';
import { AxisBottom } from '../AxisBottom';

describe('AxisBottom', () => {
  it('renders ticks from scale', () => {
    const scale = d3.scaleLinear().domain([0, 100]).range([0, 500]);
    const { container } = render(
      <svg>
        <AxisBottom xScale={scale} pixelsPerTick={100} height={400} />
      </svg>
    );
    expect(container.querySelectorAll('g').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('text').length).toBeGreaterThan(0);
  });

  it('renders with different tick density', () => {
    const scale = d3.scaleLinear().domain([0, 100]).range([0, 500]);
    const { container } = render(
      <svg>
        <AxisBottom xScale={scale} pixelsPerTick={200} height={400} />
      </svg>
    );
    expect(container.querySelectorAll('line').length).toBeGreaterThan(0);
  });
});
