"use client";

interface DataPoint {
  label: string;
  value: number;
}

interface LineChartProps {
  data: DataPoint[];
  width?: number;
  height?: number;
  color?: string;
  showDots?: boolean;
}

export default function LineChart({
  data,
  width = 600,
  height = 200,
  color = "#1b6ca8",
  showDots = true,
}: LineChartProps) {
  if (!data || data.length === 0) {
    return (
      <svg width={width} height={height}>
        <text x={width / 2} y={height / 2} textAnchor="middle" fill="#9ca3af" fontSize="13">
          No data
        </text>
      </svg>
    );
  }

  const padLeft = 52;
  const padRight = 16;
  const padTop = 16;
  const padBottom = 40;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const values = data.map((d) => d.value);
  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  const xStep = chartW / Math.max(data.length - 1, 1);

  const toX = (i: number) => padLeft + i * xStep;
  const toY = (v: number) => padTop + chartH - ((v - minVal) / range) * chartH;

  const pathD = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${toX(i).toFixed(1)} ${toY(d.value).toFixed(1)}`)
    .join(" ");

  const areaD =
    pathD +
    ` L ${toX(data.length - 1).toFixed(1)} ${(padTop + chartH).toFixed(1)}` +
    ` L ${toX(0).toFixed(1)} ${(padTop + chartH).toFixed(1)} Z`;

  // Y axis ticks
  const tickCount = 4;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const frac = i / tickCount;
    const val = minVal + frac * range;
    const y = toY(val);
    return { val, y };
  });

  // X axis labels — show at most 8 evenly spaced
  const maxLabels = 8;
  const labelStep = Math.max(1, Math.ceil(data.length / maxLabels));

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      style={{ display: "block", maxWidth: width }}
    >
      {/* Area fill */}
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0.01" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#areaGrad)" />

      {/* Grid lines */}
      {yTicks.map(({ val, y }, i) => (
        <g key={i}>
          <line
            x1={padLeft}
            y1={y}
            x2={padLeft + chartW}
            y2={y}
            stroke="#e5e7eb"
            strokeWidth="1"
          />
          <text
            x={padLeft - 8}
            y={y}
            textAnchor="end"
            dominantBaseline="middle"
            fontSize="11"
            fill="#9ca3af"
          >
            {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(0)}
          </text>
        </g>
      ))}

      {/* Line */}
      <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />

      {/* Dots */}
      {showDots &&
        data.map((d, i) => (
          <circle
            key={i}
            cx={toX(i)}
            cy={toY(d.value)}
            r="3.5"
            fill={color}
            stroke="#fff"
            strokeWidth="1.5"
          />
        ))}

      {/* X axis labels */}
      {data.map((d, i) => {
        if (i % labelStep !== 0 && i !== data.length - 1) return null;
        return (
          <text
            key={i}
            x={toX(i)}
            y={padTop + chartH + 18}
            textAnchor="middle"
            fontSize="11"
            fill="#9ca3af"
          >
            {d.label.length > 8 ? d.label.slice(5) : d.label}
          </text>
        );
      })}

      {/* Axes */}
      <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
      <line x1={padLeft} y1={padTop + chartH} x2={padLeft + chartW} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
    </svg>
  );
}
