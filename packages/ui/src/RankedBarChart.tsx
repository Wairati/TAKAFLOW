// A magnitude comparison across many categories (e.g. branches) is a bar
// chart, not a pie — and since it's comparing one measure's size, not
// identity, it's a single sequential hue rather than a categorical palette.
export interface BarDatum {
  label: string;
  value: number;
}

export function RankedBarChart({
  data,
  color = "#044b39",
  valueFormatter = (v: number) => v.toLocaleString(),
}: {
  data: BarDatum[];
  color?: string;
  valueFormatter?: (value: number) => string;
}) {
  const sorted = [...data].sort((a, b) => b.value - a.value);
  const maxValue = Math.max(1, ...sorted.map((d) => d.value));

  if (sorted.length === 0) {
    return <p className="text-sm text-ink/50">No data in this range.</p>;
  }

  return (
    <div className="space-y-2.5">
      {sorted.map((d) => (
        <div key={d.label}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="font-medium text-ink">{d.label}</span>
            <span className="text-ink/60">{valueFormatter(d.value)}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-black/5">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${(d.value / maxValue) * 100}%`, backgroundColor: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
