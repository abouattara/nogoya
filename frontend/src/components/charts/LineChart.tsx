"use client";

import { useId, useState } from "react";
import { formatShortDate } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

/**
 * Hand-rolled responsive SVG line chart.
 *
 * Deliberately dependency-free: a charting library would add far more
 * weight than these ~100 lines, and the design-system violet is applied
 * directly through CSS custom properties.
 */
export function LineChart({
  data,
  label,
  height = 160,
}: {
  data: SeriesPoint[];
  label: string;
  height?: number;
}) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);

  const width = 600; // viewBox units; the SVG scales to its container
  const padding = { top: 12, right: 8, bottom: 22, left: 30 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const total = data.reduce((sum, point) => sum + point.value, 0);
  if (data.length === 0 || total === 0) {
    return <ChartEmptyState label={label} />;
  }

  const max = Math.max(...data.map((point) => point.value), 1);
  const stepX = data.length > 1 ? innerWidth / (data.length - 1) : 0;

  const pointAt = (index: number, value: number) => ({
    x: padding.left + index * stepX,
    y: padding.top + innerHeight - (value / max) * innerHeight,
  });

  const linePath = data
    .map((point, index) => {
      const { x, y } = pointAt(index, point.value);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const areaPath =
    `${linePath} L${(padding.left + (data.length - 1) * stepX).toFixed(1)},${padding.top + innerHeight} ` +
    `L${padding.left},${padding.top + innerHeight} Z`;

  const ticks = [0, Math.round(max / 2), max];
  const active = hover !== null ? data[hover] : null;

  return (
    <figure className="w-full">
      <figcaption className="mb-1 flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-xs text-foreground-muted">
          {active ? `${formatShortDate(active.date)} · ${active.value}` : `${total} au total`}
        </span>
      </figcaption>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${label} : ${total} au total sur la période`}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand-500)" stopOpacity="0.30" />
            <stop offset="100%" stopColor="var(--brand-500)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((tick) => {
          const y = padding.top + innerHeight - (tick / max) * innerHeight;
          return (
            <g key={tick}>
              <line
                x1={padding.left}
                x2={width - padding.right}
                y1={y}
                y2={y}
                stroke="var(--border)"
                strokeWidth="1"
              />
              <text x={0} y={y + 3} fontSize="9" fill="var(--foreground-muted)">
                {tick}
              </text>
            </g>
          );
        })}

        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path
          d={linePath}
          fill="none"
          stroke="var(--brand-600)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {data.map((point, index) => {
          const { x, y } = pointAt(index, point.value);
          return (
            <g key={point.date}>
              {hover === index && <circle cx={x} cy={y} r="4" fill="var(--brand-700)" />}
              {/* Invisible wide target so hovering is easy on touch too. */}
              <rect
                x={x - stepX / 2}
                y={padding.top}
                width={Math.max(stepX, 6)}
                height={innerHeight}
                fill="transparent"
                onMouseEnter={() => setHover(index)}
              />
            </g>
          );
        })}

        <text x={padding.left} y={height - 6} fontSize="9" fill="var(--foreground-muted)">
          {formatShortDate(data[0].date)}
        </text>
        <text
          x={width - padding.right}
          y={height - 6}
          fontSize="9"
          textAnchor="end"
          fill="var(--foreground-muted)"
        >
          {formatShortDate(data[data.length - 1].date)}
        </text>
      </svg>
    </figure>
  );
}

export function ChartEmptyState({ label }: { label: string }) {
  return (
    <figure className="w-full">
      <figcaption className="mb-1 text-sm font-medium">{label}</figcaption>
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-sm text-foreground-muted">
        Pas encore assez de données
      </div>
    </figure>
  );
}
