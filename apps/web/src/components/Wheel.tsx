"use client";

import type { WheelSegment } from "@fbgroup/api-client";

interface WheelProps {
  segments: WheelSegment[];
  rotation: number; // degrees
  spinning: boolean;
  size?: number;
}

/**
 * Polar → cartesian for SVG pie slices.
 * Angle measured clockwise from the top (12 o'clock).
 */
function polarToXY(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

export default function Wheel({ segments, rotation, spinning, size = 280 }: WheelProps) {
  const n = segments.length;
  const cx = size / 2;
  const cy = size / 2;
  const rim = Math.round(size * 0.055); // gold rim thickness
  const r = size / 2 - rim - 2; // slice radius (inside the rim)
  const bulbCount = 16;
  const bulbR = size / 2 - rim / 2; // bulbs sit on the rim centreline

  if (n === 0) {
    return (
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="#e5e7eb" />
      </svg>
    );
  }

  const segAngle = 360 / n;

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        margin: "0 auto",
        filter: "drop-shadow(0 12px 26px rgba(0,0,0,0.4))",
      }}
    >
      {/* fancy gold-knobbed pointer */}
      <div className="wheel-pointer" />
      <div className="wheel-pointer-knob" />

      {/* ── rotating slices ── */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{
          position: "absolute",
          inset: 0,
          transform: `rotate(${rotation}deg)`,
          transition: spinning
            ? "transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)"
            : "none",
        }}
      >
        <defs>
          <radialGradient id="wheelShade" cx="50%" cy="50%" r="50%">
            <stop offset="58%" stopColor="#000" stopOpacity="0" />
            <stop offset="100%" stopColor="#000" stopOpacity="0.28" />
          </radialGradient>
          <radialGradient id="wheelGloss" cx="38%" cy="30%" r="65%">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.35" />
            <stop offset="45%" stopColor="#fff" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
        </defs>

        {segments.map((seg, i) => {
          const start = i * segAngle;
          const end = (i + 1) * segAngle;
          const [x1, y1] = polarToXY(cx, cy, r, start);
          const [x2, y2] = polarToXY(cx, cy, r, end);
          const largeArc = segAngle > 180 ? 1 : 0;
          const d = `M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;

          const midAngle = start + segAngle / 2;
          const [lx, ly] = polarToXY(cx, cy, r * 0.62, midAngle);

          return (
            <g key={i}>
              <path d={d} fill={seg.color} stroke="#fff7e6" strokeWidth="1.5" />
              <text
                x={lx}
                y={ly}
                fill="#fff"
                fontSize={n > 6 ? 10 : 12}
                fontWeight="800"
                textAnchor="middle"
                dominantBaseline="middle"
                transform={`rotate(${midAngle} ${lx} ${ly})`}
                style={{ pointerEvents: "none", textShadow: "0 1px 2px rgba(0,0,0,0.55)" }}
              >
                {seg.label.length > 12 ? seg.label.slice(0, 11) + "…" : seg.label}
              </text>
            </g>
          );
        })}

        {/* depth shade + top gloss over the slices */}
        <circle cx={cx} cy={cy} r={r} fill="url(#wheelShade)" pointerEvents="none" />
        <circle cx={cx} cy={cy} r={r} fill="url(#wheelGloss)" pointerEvents="none" />
      </svg>

      {/* ── static frame: gold rim + chasing bulbs + hub ── */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        <defs>
          <linearGradient id="wheelGold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fff3bf" />
            <stop offset="35%" stopColor="#f4c430" />
            <stop offset="70%" stopColor="#c8961f" />
            <stop offset="100%" stopColor="#8b6508" />
          </linearGradient>
          <radialGradient id="wheelHub" cx="38%" cy="32%" r="70%">
            <stop offset="0%" stopColor="#fff7c2" />
            <stop offset="45%" stopColor="#ffd84d" />
            <stop offset="80%" stopColor="#e0a200" />
            <stop offset="100%" stopColor="#9c6a0c" />
          </radialGradient>
        </defs>

        {/* gold rim ring + edge lines */}
        <circle cx={cx} cy={cy} r={size / 2 - rim / 2 - 1} fill="none" stroke="url(#wheelGold)" strokeWidth={rim} />
        <circle cx={cx} cy={cy} r={r + 1.5} fill="none" stroke="#6e4a08" strokeWidth="1.5" />
        <circle cx={cx} cy={cy} r={size / 2 - 1} fill="none" stroke="#6e4a08" strokeWidth="1.5" />

        {/* chasing bulbs around the rim */}
        {Array.from({ length: bulbCount }).map((_, i) => {
          const [bx, by] = polarToXY(cx, cy, bulbR, (i / bulbCount) * 360);
          return (
            <circle
              key={i}
              cx={bx}
              cy={by}
              r={size * 0.013}
              className="wheel-bulb"
              style={{ animationDelay: `${(i % 2) * 0.5}s` }}
            />
          );
        })}

        {/* hub */}
        <circle cx={cx} cy={cy} r={size * 0.1} fill="url(#wheelHub)" stroke="#8b6508" strokeWidth="2" />
        <circle cx={cx} cy={cy} r={size * 0.046} fill="#7a1f1f" stroke="#ffd84d" strokeWidth="1.5" />
        <text
          x={cx}
          y={cy}
          fill="#ffd84d"
          fontSize={size * 0.06}
          fontWeight="900"
          textAnchor="middle"
          dominantBaseline="central"
        >
          ★
        </text>
      </svg>
    </div>
  );
}
