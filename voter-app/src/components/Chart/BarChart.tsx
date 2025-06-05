import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface BarChartProps {
  data: { label: string; value: number }[];
}

const BarChart: React.FC<BarChartProps> = ({ data }) => {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (data && ref.current) {
      // Clear previous rendering
      d3.select(ref.current).selectAll("*").remove();

      const svg = d3.select(ref.current);
      const margin = { top: 20, right: 30, bottom: 30, left: 40 };
      const width = 800 - margin.left - margin.right;
      const height = 400 - margin.top - margin.bottom;

      const x = d3
        .scaleBand()
        .domain(data.map((d) => d.label))
        .range([0, width])
        .padding(0.1);

      const y = d3
        .scaleLinear()
        .domain([0, d3.max(data, (d) => d.value) as number])
        .nice()
        .range([height, 0]);

      svg
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`)
        .selectAll(".bar")
        .data(data)
        .enter()
        .append("rect")
        .attr("class", "bar")
        .attr("x", (d) => x(d.label)!)
        .attr("y", (d) => y(d.value))
        .attr("width", x.bandwidth())
        .attr("height", (d) => height - y(d.value))
        .attr("fill", "steelblue");

      svg
        .append("g")
        .attr("transform", `translate(${margin.left},${height + margin.top})`)
        .call(d3.axisBottom(x));

      svg
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`)
        .call(d3.axisLeft(y));
    }
  }, [data]);

  return <svg ref={ref} width={800} height={400}></svg>;
};

export default BarChart;
