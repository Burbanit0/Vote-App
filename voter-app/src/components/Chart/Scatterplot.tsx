import * as d3 from "d3";
import { AxisLeft } from "./AxisLeft";
import { AxisBottom } from "./AxisBottom";
import { useState } from "react";
import { InteractionData, Tooltip } from "./Tooltip";

const MARGIN = { top: 50, right: 50, bottom: 50, left: 50 };

type DataPoint = {
  x: number;
  y: number;
  size: number;
  group: string;
};

type ScatterplotProps = {
  width: number;
  height: number;
  data: DataPoint[];
};

export const Scatterplot = ({ width, height, data }: ScatterplotProps) => {
  const boundsWidth = width - MARGIN.right - MARGIN.left;
  const boundsHeight = height - MARGIN.top - MARGIN.bottom;

  const [hovered, setHovered] = useState<InteractionData | null>(null);

  // Scales
  const yScale = d3.scaleLinear().domain([-5, 5]).range([boundsHeight, 0]);
  const xScale = d3
    .scaleLinear()
    .domain([-5, 5])
    .range([0, boundsWidth]);
  const allGroups = data.map((d) => String(d.group));
  const colorScale = d3
    .scaleOrdinal<string>()
    .domain(allGroups)
    .range(["#e0ac2b", "#e85252", "#6689c6", "#9a6fb0", "#a53253"]);

  // Build the shapes
  const allShapes = data.map((d, i) => {
    return (
      <circle
        key={i}
        r={8}
        cx={xScale(d.x)}
        cy={yScale(d.y)}
        stroke={colorScale(d.group)}
        fill={colorScale(d.group)}
        fillOpacity={0.7}
        onMouseEnter={() =>
          setHovered({
            xPos: xScale(d.x),
            yPos: yScale(d.y),
            name: d.group,
            
          })
        }
        onMouseLeave={() => setHovered(null)}
      />
    );
  });

  return (
    <div style={{ position: "relative" }}>
      <svg width={width} height={height}>
        <g
          width={boundsWidth}
          height={boundsHeight}
          transform={`translate(${[MARGIN.left, MARGIN.top].join(",")})`}
        >
          {/* Y axis */}
          <AxisLeft yScale={yScale} pixelsPerTick={20} width={boundsWidth} />
          <line
          x1={0}
          x2={boundsWidth}
          y1={boundsHeight/2}
          y2={boundsHeight/2}
          stroke="#ababab"
          strokeDasharray="2"
          />  
          <line
          x1={boundsWidth/2}
          x2={boundsWidth/2}
          y1={0}
          y2={boundsHeight}
          stroke="#ababab"
          strokeDasharray="2"
          /> 
          {/* X axis, use an additional translation to appear at the bottom */}
          <g transform={`translate(0, ${boundsHeight})`}>
            <AxisBottom
              xScale={xScale}
              pixelsPerTick={20}
              height={boundsHeight}
            />
          </g>

          {/* Circles */}
          {allShapes}
        </g>
      </svg>

      {/* Tooltip */}
      <div
        style={{
          width: boundsWidth,
          height: boundsHeight,
          position: "absolute",
          top: 0,
          left: 0,
          pointerEvents: "none",
          marginLeft: MARGIN.left,
          marginTop: MARGIN.top,
        }}
      >
        <Tooltip interactionData={hovered} />
      </div>
    </div>
  );
};
