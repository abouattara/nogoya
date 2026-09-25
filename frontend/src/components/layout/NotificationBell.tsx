"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/client-api";
import { formatRelativeTime } from "@/lib/format";
import type { AppNotification, Paginated } from "@/lib/types";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: counter } = useQuery({
    queryKey: ["notifications-unread"],
    queryFn: () => apiFetch<{ unread_count: number }>("/api/v1/notifications/unread-count/"),
    refetchInterval: 15_000,
  });

  const { data: list, isLoading } = useQuery({
    queryKey: ["notifications-preview"],
    queryFn: () => apiFetch<Paginated<AppNotification>>("/api/v1/notifications/"),
    enabled: open,
  });

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const unread = counter?.unread_count ?? 0;

  async function markRead(notification: AppNotification) {
    if (notification.is_read) return;
    await apiFetch(`/api/v1/notifications/${notification.id}/read/`, { method: "POST" });
    queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-preview"] });
  }

  async function markAllRead() {
    await apiFetch("/api/v1/notifications/read-all/", { method: "POST" });
    queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-preview"] });
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={unread > 0 ? `Notifications (${unread} non lues)` : "Notifications"}
        aria-expanded={open}
        aria-haspopup="menu"
        className="relative flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-surface-muted"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-medium text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-border bg-surface shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-2">
            <p className="text-sm font-semibold">Notifications</p>
            {unread > 0 && (
              <button onClick={markAllRead} className="text-xs text-brand-700 hover:underline">
                Tout marquer comme lu
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {isLoading && <p className="px-4 py-6 text-sm text-foreground-muted">Chargement...</p>}
            {!isLoading && (list?.results.length ?? 0) === 0 && (
              <p className="px-4 py-6 text-sm text-foreground-muted">Aucune notification pour le moment.</p>
            )}
            {list?.results.slice(0, 6).map((notification) => (
              <Link
                key={notification.id}
                href={notification.url || "/notifications"}
                onClick={() => {
                  markRead(notification);
                  setOpen(false);
                }}
                className={`block border-b border-border px-4 py-3 last:border-b-0 hover:bg-surface-muted ${
                  notification.is_read ? "" : "bg-brand-50"
                }`}
              >
                <p className="text-sm font-medium text-foreground">{notification.title}</p>
                {notification.message && (
                  <p className="line-clamp-2 text-xs text-foreground-muted">{notification.message}</p>
                )}
                <p className="mt-1 text-[11px] text-foreground-muted">
                  {formatRelativeTime(notification.created_at)}
                </p>
              </Link>
            ))}
          </div>

          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-border px-4 py-2 text-center text-sm font-medium text-brand-700 hover:bg-surface-muted"
          >
            Voir toutes les notifications
          </Link>
        </div>
      )}
    </div>
  );
}
