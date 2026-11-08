// Simple SVG area chart, no chart library needed
export default function AreaChart({ points, height = 190 }) {
  if (!points.length) return <div className="chart-empty">No readings yet</div>;
  const width = 800;
  const padRight = 54;
  const max = Math.max(...points.map((p) => p.value), 1);
  const top = Math.ceil(max / 10) * 10 || 10;
  const x = (i) => (points.length === 1 ? 0 : (i / (points.length - 1)) * (width - padRight));
  const y = (v) => height - 12 - (v / top) * (height - 30);

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ");
  const area = `${line} L${x(points.length - 1)},${height} L0,${height} Z`;
  const last = points[points.length - 1];
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(top * f));

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--red)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--red)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {ticks.map((t) => (
        <g key={t}>
          <line x1="0" x2={width - padRight} y1={y(t)} y2={y(t)} className="chart-grid" />
          <text x={width - 6} y={y(t) + 4} className="chart-tick" textAnchor="end">{t}</text>
        </g>
      ))}
      <path d={area} fill="url(#fill)" />
      <path d={line} className="chart-line" />
      <circle cx={x(points.length - 1)} cy={y(last.value)} r="4.5" className="chart-dot" />
    </svg>
  );
}
