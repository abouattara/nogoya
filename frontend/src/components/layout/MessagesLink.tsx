"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/client-api";

export function MessagesLink({ compact = false }: { compact?: boolean }) {
  const { data } = useQuery({
    queryKey: ["unread-count"],
    queryFn: () => apiFetch<{ unread_count: number }>("/api/v1/conversations/unread-count/"),
    refetchInterval: 15_000,
  });
  const count = data?.unread_count ?? 0;

  if (compact) {
    return (
      <Link href="/compte/messages" className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-surface-muted">
        Messages
        {count > 0 && (
          <span className="rounded-full bg-brand-600 px-1.5 py-0.5 text-xs font-medium text-white">{count}</span>
        )}
      </Link>
    );
  }

  return (
    <Link href="/compte/messages" className="relative text-sm font-medium hover:text-brand-dark">
      Messages
      {count > 0 && (
        <span className="absolute -right-3 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-medium text-white">
          {count}
        </span>
      )}
    </Link>
  );
}
