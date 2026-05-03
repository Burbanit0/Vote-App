import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DensityChartProps {
  data: { x: number; y: number }[];
  gridSize?: number;
}

const DensityChart: React.FC<DensityChartProps> = ({ data, gridSize = 20 }) => {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (data && ref.current) {
      // Clear previous rendering
      d3.select(ref.current).selectAll('*').remove();

      const svg = d3.select(ref.current);
      const margin = { top: 20, right: 30, bottom: 30, left: 40 };
      const width = 600 - margin.left - margin.right;
      const height = 400 - margin.top - margin.bottom;

      // Define scales
      const x = d3.scaleLinear().domain([-1, 1]).range([0, width]);

      const y = d3.scaleLinear().domain([-1, 1]).range([height, 0]);

      // Calculate density
      const xTicks = d3.ticks(-1, 1, gridSize);
      const yTicks = d3.ticks(-1, 1, gridSize);

      const densityData = xTicks.map((xVal) =>
        yTicks.map((yVal) => {
          const filtered = data.filter(
            (d) =>
              d.x >= xVal && d.x < xVal + 1 / gridSize && d.y >= yVal && d.y < yVal + 1 / gridSize
          );
          return { x: xVal, y: yVal, value: filtered.length };
        })
      );

      // Define color scale
      const colorScale = d3
        .scaleSequential(d3.interpolateViridis)
        .domain([0, d3.max(densityData.flat(), (d) => d.value) as number]);

      // Draw density grid
      svg
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`)
        .selectAll('rect')
        .data(densityData.flat())
        .enter()
        .append('rect')
        .attr('x', (d) => x(d.x))
        .attr('y', (d) => y(d.y + 1 / gridSize))
        .attr('width', x(1 / gridSize) - x(0))
        .attr('height', y(0) - y(1 / gridSize))
        .attr('fill', (d) => colorScale(d.value))
        .attr('opacity', 0.7);

      // Add axes
      svg
        .append('g')
        .attr('transform', `translate(${margin.left},${height + margin.top})`)
        .call(d3.axisBottom(x).ticks(5));

      svg
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`)
        .call(d3.axisLeft(y).ticks(5));
    }
  }, [data, gridSize]);

  return <svg ref={ref} width={600} height={400}></svg>;
};

export default DensityChart;
