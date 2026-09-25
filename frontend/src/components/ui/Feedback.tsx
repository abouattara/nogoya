import { clsx } from "clsx";
import type { ReactNode } from "react";

type BadgeTone = "neutral" | "brand" | "success" | "warning" | "danger";

// Explicit background/foreground pair per tone — each combination checked
// for >= 4.5:1 contrast (see ARCHITECTURE.md Design System audit).
const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-foreground-muted",
  brand: "bg-brand-100 text-brand-800",
  success: "bg-success-bg text-success-fg",
  warning: "bg-warning-bg text-warning-fg",
  danger: "bg-danger-bg text-danger-fg",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", BADGE_TONES[tone])}>
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={clsx("animate-spin", className)} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-lg bg-surface-muted", className)} />;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
      <p className="text-base font-medium">{title}</p>
      {description && <p className="max-w-sm text-sm text-foreground-muted">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-danger-fg/20 bg-danger-bg py-10 text-center">
      <p className="text-sm font-medium text-danger-fg">{message}</p>
      {retry && (
        <button onClick={retry} className="text-sm font-medium text-danger-fg underline underline-offset-2">
          Réessayer
        </button>
      )}
    </div>
  );
}
