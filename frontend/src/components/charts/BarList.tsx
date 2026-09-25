"use client";

import Link from "next/link";
import { ChartEmptyState } from "./LineChart";

export interface BarItem {
  label: string;
  value: number;
  href?: string;
}

/**
 * Horizontal bar list — used for "top produits" and the status breakdown.
 * Reads as a plain list for screen readers; the bars are decorative.
 */
export function BarList({ title, items, unit = "" }: { title: string; items: BarItem[]; unit?: string }) {
  const meaningful = items.filter((item) => item.value > 0);
  if (meaningful.length === 0) return <ChartEmptyState label={title} />;

  const max = Math.max(...meaningful.map((item) => item.value));

  return (
    <section>
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      <ul className="flex flex-col gap-2">
        {meaningful.map((item) => (
          <li key={item.label}>
            <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
              {item.href ? (
                <Link href={item.href} className="truncate text-brand-700 hover:underline">
                  {item.label}
                </Link>
              ) : (
                <span className="truncate text-foreground">{item.label}</span>
              )}
              <span className="shrink-0 text-xs text-foreground-muted">
                {item.value}
                {unit && ` ${unit}`}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-surface-muted" aria-hidden="true">
              <div
                className="h-full rounded-full bg-brand-500"
                style={{ width: `${Math.max(4, (item.value / max) * 100)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
