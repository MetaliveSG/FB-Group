"use client";

interface DataPoint {
  label: string;
  value: number;
}

interface BarChartProps {
  data: DataPoint[];
  width?: number;
  height?: number;
  color?: string;
  horizontal?: boolean;
}

export default function BarChart({
  data,
  width = 500,
  height = 220,
  color = "#0f4c75",
  horizontal = false,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <svg width={width} height={height}>
        <text x={width / 2} y={height / 2} textAnchor="middle" fill="#9ca3af" fontSize="13">
          No data
        </text>
      </svg>
    );
  }

  const padLeft = horizontal ? 100 : 48;
  const padRight = 16;
  const padTop = 12;
  const padBottom = horizontal ? 32 : 44;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const values = data.map((d) => d.value);
  const maxVal = Math.max(...values, 1);

  if (horizontal) {
    const barHeight = Math.max(16, (chartH / data.length) * 0.7);
    const gap = (chartH - barHeight * data.length) / (data.length + 1);

    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ display: "block", maxWidth: width }}
      >
        {/* X grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac, i) => {
          const x = padLeft + frac * chartW;
          const val = frac * maxVal;
          return (
            <g key={i}>
              <line x1={x} y1={padTop} x2={x} y2={padTop + chartH} stroke="#e5e7eb" strokeWidth="1" />
              <text x={x} y={padTop + chartH + 14} textAnchor="middle" fontSize="11" fill="#9ca3af">
                {val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val.toFixed(0)}
              </text>
            </g>
          );
        })}

        {data.map((d, i) => {
          const barW = (d.value / maxVal) * chartW;
          const y = padTop + gap + i * (barHeight + gap);
          return (
            <g key={i}>
              <text
                x={padLeft - 6}
                y={y + barHeight / 2}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize="12"
                fill="#374151"
              >
                {d.label.length > 12 ? d.label.slice(0, 12) + "…" : d.label}
              </text>
              <rect
                x={padLeft}
                y={y}
                width={Math.max(barW, 2)}
                height={barHeight}
                fill={color}
                rx="3"
                opacity="0.85"
              />
              {barW > 30 && (
                <text
                  x={padLeft + barW - 6}
                  y={y + barHeight / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize="11"
                  fill="#fff"
                  fontWeight="600"
                >
                  {d.value >= 1000 ? `${(d.value / 1000).toFixed(1)}k` : d.value}
                </text>
              )}
            </g>
          );
        })}

        {/* Axes */}
        <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
        <line x1={padLeft} y1={padTop + chartH} x2={padLeft + chartW} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
      </svg>
    );
  }

  // Vertical bars
  const barWidth = Math.max(12, (chartW / data.length) * 0.6);
  const gap = (chartW - barWidth * data.length) / (data.length + 1);
  const tickCount = 4;
  const yTicks = Array.from({ length: tickCount + 1 }, (_, i) => i / tickCount);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      style={{ display: "block", maxWidth: width }}
    >
      {/* Y grid */}
      {yTicks.map((frac, i) => {
        const y = padTop + chartH - frac * chartH;
        const val = frac * maxVal;
        return (
          <g key={i}>
            <line x1={padLeft} y1={y} x2={padLeft + chartW} y2={y} stroke="#e5e7eb" strokeWidth="1" />
            <text x={padLeft - 8} y={y} textAnchor="end" dominantBaseline="middle" fontSize="11" fill="#9ca3af">
              {val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val.toFixed(0)}
            </text>
          </g>
        );
      })}

      {data.map((d, i) => {
        const barH = (d.value / maxVal) * chartH;
        const x = padLeft + gap + i * (barWidth + gap);
        const y = padTop + chartH - barH;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barWidth} height={Math.max(barH, 2)} fill={color} rx="3" opacity="0.85" />
            <text
              x={x + barWidth / 2}
              y={padTop + chartH + 14}
              textAnchor="middle"
              fontSize="11"
              fill="#9ca3af"
            >
              {d.label.length > 8 ? d.label.slice(0, 8) + "…" : d.label}
            </text>
          </g>
        );
      })}

      {/* Axes */}
      <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
      <line x1={padLeft} y1={padTop + chartH} x2={padLeft + chartW} y2={padTop + chartH} stroke="#d1d5db" strokeWidth="1" />
    </svg>
  );
}
