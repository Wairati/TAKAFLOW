// Hand-rolled SVG line/area chart for a single series over time — one axis,
// one hue, with a hover crosshair + tooltip (an interactive chart is the
// baseline per the dataviz skill, not an enhancement).
import { useState } from "react";

export interface TrendPoint {
  label: string;
  value: number;
}

export function TrendChart({
  data,
  color = "#1ea97b",
  valueFormatter = (v: number) => v.toLocaleString(),
}: {
  data: TrendPoint[];
  color?: string;
  valueFormatter?: (value: number) => string;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (data.length === 0) {
    return <p className="text-sm text-ink/50">No data in this range.</p>;
  }

  const width = 640;
  const height = 220;
  const padding = { top: 16, right: 8, bottom: 26, left: 8 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(1, ...data.map((d) => d.value));

  const xFor = (i: number) => padding.left + (data.length <= 1 ? innerWidth / 2 : (i / (data.length - 1)) * innerWidth);
  const yFor = (v: number) => padding.top + innerHeight - (v / maxValue) * innerHeight;

  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(d.value)}`).join(" ");
  const areaPath = `${linePath} L ${xFor(data.length - 1)} ${padding.top + innerHeight} L ${xFor(0)} ${padding.top + innerHeight} Z`;

  const tickCount = Math.min(6, data.length);
  const tickIndices = Array.from({ length: tickCount }, (_, i) =>
    Math.round((i / Math.max(1, tickCount - 1)) * (data.length - 1))
  );
  const slotWidth = innerWidth / data.length;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        onMouseLeave={() => setHoverIndex(null)}
        role="img"
        aria-label="Trend over time"
      >
        <path d={areaPath} fill={color} fillOpacity={0.12} />
        <path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {[...new Set(tickIndices)].map((i) => (
          <text key={i} x={xFor(i)} y={height - 6} textAnchor="middle" className="fill-ink/40 text-[9px]">
            {data[i].label}
          </text>
        ))}

        {hoverIndex !== null && (
          <>
            <line
              x1={xFor(hoverIndex)}
              x2={xFor(hoverIndex)}
              y1={padding.top}
              y2={padding.top + innerHeight}
              stroke="#053438"
              strokeOpacity={0.15}
            />
            <circle cx={xFor(hoverIndex)} cy={yFor(data[hoverIndex].value)} r={4} fill={color} stroke="#fff" strokeWidth={2} />
          </>
        )}

        {data.map((_, i) => (
          <rect
            key={i}
            x={padding.left + i * slotWidth}
            y={0}
            width={slotWidth}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
          />
        ))}
      </svg>

      {hoverIndex !== null && (
        <div
          className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 -translate-y-[110%] whitespace-nowrap rounded-lg bg-ink px-2.5 py-1.5 text-xs font-semibold text-white shadow-lg"
          style={{ left: `${(xFor(hoverIndex) / width) * 100}%` }}
        >
          <div className="text-white/70">{data[hoverIndex].label}</div>
          <div>{valueFormatter(data[hoverIndex].value)}</div>
        </div>
      )}
    </div>
  );
}
