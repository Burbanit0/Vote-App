import { render } from '@testing-library/react';
import * as d3 from 'd3';
import { AxisLeft } from '../AxisLeft';

describe('AxisLeft', () => {
  it('renders ticks from scale', () => {
    const scale = d3.scaleLinear().domain([0, 100]).range([400, 0]);
    const { container } = render(
      <svg>
        <AxisLeft yScale={scale} pixelsPerTick={100} width={500} />
      </svg>
    );
    expect(container.querySelectorAll('g').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('text').length).toBeGreaterThan(0);
  });
});
