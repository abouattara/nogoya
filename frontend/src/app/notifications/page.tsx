"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";
import { formatRelativeTime } from "@/lib/format";
import type { AppNotification, Paginated } from "@/lib/types";

export default function NotificationsPage() {
  return (
    <RequireAuth>
      {() => (
        <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Notifications</h1>
          <NotificationList />
        </div>
      )}
    </RequireAuth>
  );
}

function NotificationList() {
  const queryClient = useQueryClient();
  const [onlyUnread, setOnlyUnread] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["notifications", onlyUnread],
    queryFn: () =>
      apiFetch<Paginated<AppNotification>>(
        `/api/v1/notifications/${onlyUnread ? "?unread=true" : ""}`
      ),
    refetchInterval: 30_000,
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-preview"] });
  }

  async function markRead(id: number) {
    await apiFetch(`/api/v1/notifications/${id}/read/`, { method: "POST" });
    invalidate();
  }

  async function markAllRead() {
    await apiFetch("/api/v1/notifications/read-all/", { method: "POST" });
    invalidate();
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex gap-2">
          <FilterTab active={!onlyUnread} onClick={() => setOnlyUnread(false)}>
            Toutes
          </FilterTab>
          <FilterTab active={onlyUnread} onClick={() => setOnlyUnread(true)}>
            Non lues
          </FilterTab>
        </div>
        <Button variant="secondary" size="sm" onClick={markAllRead}>
          Tout marquer comme lu
        </Button>
      </div>

      {isLoading && <Skeleton className="h-72 w-full" />}
      {isError && <ErrorState message="Impossible de charger vos notifications." retry={refetch} />}

      {data && data.results.length === 0 && (
        <EmptyState
          title={onlyUnread ? "Aucune notification non lue" : "Aucune notification"}
          description="Les nouveaux messages et les mises à jour de vos annonces apparaîtront ici."
        />
      )}

      {data && data.results.length > 0 && (
        <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border">
          {data.results.map((notification) => (
            <li
              key={notification.id}
              className={clsx("flex items-start gap-3 p-4", !notification.is_read && "bg-brand-50")}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{notification.title}</p>
                  {!notification.is_read && <Badge tone="brand">Nouveau</Badge>}
                </div>
                {notification.message && (
                  <p className="mt-0.5 text-sm text-foreground-muted">{notification.message}</p>
                )}
                <p className="mt-1 text-xs text-foreground-muted">
                  {formatRelativeTime(notification.created_at)}
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                {notification.url && (
                  <Link
                    href={notification.url}
                    onClick={() => markRead(notification.id)}
                    className="text-sm font-medium text-brand-700 hover:underline"
                  >
                    Ouvrir
                  </Link>
                )}
                {!notification.is_read && (
                  <button
                    onClick={() => markRead(notification.id)}
                    className="text-xs text-foreground-muted hover:text-foreground"
                  >
                    Marquer comme lu
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function FilterTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={clsx(
        "rounded-lg border px-3 py-1.5 text-sm transition-colors",
        active
          ? "border-brand-300 bg-brand-50 font-medium text-brand-800"
          : "border-border bg-surface text-foreground hover:bg-surface-muted"
      )}
    >
      {children}
    </button>
  );
}
