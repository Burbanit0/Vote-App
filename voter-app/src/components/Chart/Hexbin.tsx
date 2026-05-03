import * as d3 from 'd3';
import { AxisLeft } from './AxisLeft';
import { AxisBottom } from './AxisBottom';
import { hexbin } from 'd3-hexbin';
import { Key } from 'react';

const MARGIN = { top: 50, right: 50, bottom: 50, left: 50 };
const BIN_SIZE = 9;

type HexbinProps = {
  width: number;
  height: number;
  data: { x: number; y: number }[];
};

export const Hexbin = ({ width, height, data }: HexbinProps) => {
  // Layout. The div size is set by the given props.
  // The bounds (=area inside the axis) is calculated by substracting the margins
  const boundsWidth = width - MARGIN.right - MARGIN.left;
  const boundsHeight = height - MARGIN.top - MARGIN.bottom;

  // Scales
  const yScale = d3.scaleLinear().domain([-5, 5]).range([boundsHeight, 0]);
  const xScale = d3.scaleLinear().domain([-5, 5]).range([0, boundsWidth]);

  const hexbinGenerator = hexbin()
    .radius(BIN_SIZE)
    .extent([
      [0, 0],
      [boundsWidth, boundsHeight],
    ]);

  const hexbinData = hexbinGenerator(data.map((item) => [xScale(item.x), yScale(item.y)]));

  const maxItemPerBin = Math.max(...hexbinData.map((hex: string | any[]) => hex.length));

  const colorScale = d3.scaleSqrt<string>().domain([0, maxItemPerBin]).range(['black', '#cb1dd1']);

  const opacityScale = d3.scaleLinear<number>().domain([0, maxItemPerBin]).range([0.2, 1]);

  // Build the shapes
  const allShapes = hexbinData.map(
    (d: { x: string; y: string; length: d3.NumberValue }, i: Key | null | undefined) => {
      return (
        <path
          key={i}
          d={hexbinGenerator.hexagon()}
          transform={'translate(' + d.x + ',' + d.y + ')'}
          opacity={1}
          stroke={'white'}
          fill={colorScale(d.length)}
          // fillOpacity={opacityScale(d.length)}
          strokeOpacity={opacityScale(d.length)}
          strokeWidth={0.5}
        />
      );
    }
  );

  return (
    <div>
      <svg width={width} height={height}>
        {/* first group is for the violin and box shapes */}
        <g
          width={boundsWidth}
          height={boundsHeight}
          transform={`translate(${[MARGIN.left, MARGIN.top].join(',')})`}
        >
          {/* Y axis */}
          <AxisLeft yScale={yScale} pixelsPerTick={100} width={boundsWidth} />

          {/* X axis, use an additional translation to appear at the bottom */}
          <g transform={`translate(0, ${boundsHeight})`}>
            <AxisBottom xScale={xScale} pixelsPerTick={100} height={boundsHeight} />
          </g>

          {/* Circles */}
          {allShapes}
        </g>
      </svg>
    </div>
  );
};
