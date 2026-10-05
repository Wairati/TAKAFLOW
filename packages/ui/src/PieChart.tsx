// Hand-rolled SVG donut chart — no charting dependency. Categorical hues are
// assigned in a fixed order (never cycled/reassigned when the data changes)
// and validated for colorblind-safety; a 6th+ slice folds into gray rather
// than generating a new hue. See the dataviz skill for the method this follows.
import { useState } from "react";

const CATEGORICAL_COLORS = ["#1ea97b", "#2180e6", "#d97706", "#72c613", "#9333ea"];
const OVERFLOW_COLOR = "#94a3b8";

export interface PieSlice {
  label: string;
  value: number;
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(angleRad), y: cy + r * Math.sin(angleRad) };
}

function arcPath(cx: number, cy: number, rOuter: number, rInner: number, startAngle: number, endAngle: number) {
  const clampedEnd = Math.min(endAngle, startAngle + 359.99);
  const startOuter = polarToCartesian(cx, cy, rOuter, clampedEnd);
  const endOuter = polarToCartesian(cx, cy, rOuter, startAngle);
  const startInner = polarToCartesian(cx, cy, rInner, clampedEnd);
  const endInner = polarToCartesian(cx, cy, rInner, startAngle);
  const largeArc = clampedEnd - startAngle > 180 ? 1 : 0;
  return [
    "M", startOuter.x, startOuter.y,
    "A", rOuter, rOuter, 0, largeArc, 0, endOuter.x, endOuter.y,
    "L", endInner.x, endInner.y,
    "A", rInner, rInner, 0, largeArc, 1, startInner.x, startInner.y,
    "Z",
  ].join(" ");
}

export function PieChart({
  data,
  valueFormatter = (v: number) => v.toLocaleString(),
}: {
  data: PieSlice[];
  valueFormatter?: (value: number) => string;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const total = data.reduce((sum, d) => sum + d.value, 0);

  if (data.length === 0 || total <= 0) {
    return <p className="text-sm text-ink/50">No data in this range.</p>;
  }

  let cumulative = 0;
  const slices = data.map((d, i) => {
    const startAngle = (cumulative / total) * 360;
    cumulative += d.value;
    const endAngle = (cumulative / total) * 360;
    return {
      ...d,
      startAngle,
      endAngle,
      color: i < CATEGORICAL_COLORS.length ? CATEGORICAL_COLORS[i] : OVERFLOW_COLOR,
      pct: (d.value / total) * 100,
    };
  });

  const focused = hoverIndex !== null ? slices[hoverIndex] : null;

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row">
      <svg viewBox="0 0 200 200" className="h-40 w-40 shrink-0" role="img" aria-label="Breakdown by material">
        {slices.map((s, i) => (
          <path
            key={s.label}
            d={arcPath(100, 100, hoverIndex === i ? 95 : 90, 55, s.startAngle, s.endAngle)}
            fill={s.color}
            stroke="#fff"
            strokeWidth={2}
            className="cursor-default transition-[d]"
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(null)}
          />
        ))}
        <text x="100" y="97" textAnchor="middle" className="fill-ink text-[15px] font-bold">
          {valueFormatter(focused ? focused.value : total)}
        </text>
        <text x="100" y="114" textAnchor="middle" className="fill-ink/45 text-[9px]">
          {focused ? focused.label : "Total"}
        </text>
      </svg>

      {/* Legend doubles as direct labels — identity is never color-alone. */}
      <ul className="w-full space-y-1.5 text-sm">
        {slices.map((s, i) => (
          <li
            key={s.label}
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(null)}
            className={`flex items-center justify-between gap-3 rounded-lg px-2 py-1 transition ${
              hoverIndex === i ? "bg-black/5" : ""
            }`}
          >
            <span className="flex items-center gap-2 text-ink/75">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
              {s.label}
            </span>
            <span className="shrink-0 font-semibold text-ink">
              {valueFormatter(s.value)} ({s.pct.toFixed(0)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
