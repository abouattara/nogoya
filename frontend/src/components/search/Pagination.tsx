import Link from "next/link";
import clsx from "clsx";

export function Pagination({
  page,
  hasNext,
  hasPrevious,
  basePath,
  searchParams,
}: {
  page: number;
  hasNext: boolean;
  hasPrevious: boolean;
  basePath: string;
  searchParams: Record<string, string | undefined>;
}) {
  if (!hasNext && !hasPrevious) return null;

  function hrefFor(target: number) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined && key !== "page") params.set(key, value);
    }
    if (target > 1) params.set("page", String(target));
    const qs = params.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  }

  return (
    <div className="mt-8 flex items-center justify-center gap-3">
      <Link
        href={hrefFor(page - 1)}
        aria-disabled={!hasPrevious}
        className={clsx(
          "rounded-lg border border-border px-3 py-1.5 text-sm",
          !hasPrevious ? "pointer-events-none opacity-40" : "hover:bg-surface-muted"
        )}
      >
        ← Précédent
      </Link>
      <span className="text-sm text-foreground-muted">Page {page}</span>
      <Link
        href={hrefFor(page + 1)}
        aria-disabled={!hasNext}
        className={clsx(
          "rounded-lg border border-border px-3 py-1.5 text-sm",
          !hasNext ? "pointer-events-none opacity-40" : "hover:bg-surface-muted"
        )}
      >
        Suivant →
      </Link>
    </div>
  );
}
