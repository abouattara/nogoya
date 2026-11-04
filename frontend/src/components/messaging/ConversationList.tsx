"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import clsx from "clsx";
import { Avatar } from "@/components/messaging/Avatar";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { apiFetch } from "@/lib/client-api";
import { formatRelativeTime } from "@/lib/format";
import type { ConversationSummary, Paginated } from "@/lib/types";

/**
 * La liste des fils, posee deux fois : en colonne a cote de la
 * conversation sur grand ecran, et seule sur telephone.
 *
 * Elle porte son propre `useQuery`. Les deux instances ne coexistent
 * jamais — l'une est masquee par `lg:` — et TanStack Query sert de toute
 * facon le meme cache sous la meme cle : rien n'est charge deux fois.
 */
export function ConversationList({
  activeId,
  className,
}: {
  activeId?: string;
  className?: string;
}) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => apiFetch<Paginated<ConversationSummary>>("/api/v1/conversations/"),
    refetchInterval: 10_000,
  });

  if (isLoading) {
    return (
      <div className={clsx("flex flex-col gap-2", className)}>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className={className}>
        <ErrorState message="Impossible de charger vos messages." retry={refetch} />
      </div>
    );
  }
  if (data.results.length === 0) {
    return (
      <div className={className}>
        <EmptyState
          title="Aucune conversation"
          description="Faites une demande depuis une annonce : l'équipe NOGOYA vous répond ici."
        />
      </div>
    );
  }

  return (
    <ul className={clsx("flex flex-col", className)}>
      {data.results.map((conv) => {
        const active = activeId === String(conv.id);
        const unread = conv.unread_count > 0;
        return (
          <li key={conv.id}>
            <Link
              href={`/compte/messages/${conv.id}`}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "flex items-center gap-3 border-l-2 px-3 py-3 transition-colors",
                active
                  ? "border-brand-600 bg-brand-50"
                  : "border-transparent hover:bg-surface-muted"
              )}
            >
              <Avatar name={conv.other_participant.full_name} src={conv.other_participant.avatar} />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className={clsx("truncate", unread ? "font-semibold" : "font-medium")}>
                    {conv.other_participant.full_name}
                  </span>
                  {conv.last_message && (
                    <span className="shrink-0 text-[11px] text-foreground-muted">
                      {formatRelativeTime(conv.last_message.created_at)}
                    </span>
                  )}
                </span>
                <span className="mt-0.5 flex items-center gap-2">
                  <span
                    className={clsx(
                      "truncate text-sm",
                      unread ? "text-foreground" : "text-foreground-muted"
                    )}
                  >
                    {conv.last_message
                      ? (conv.last_message.is_mine ? "Vous : " : "") + conv.last_message.body
                      : "Nouvelle conversation"}
                  </span>
                  {unread && (
                    <span
                      className="ml-auto flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-brand-600 px-1.5 text-[11px] font-semibold text-white"
                      aria-label={`${conv.unread_count} message${conv.unread_count > 1 ? "s" : ""} non lu${conv.unread_count > 1 ? "s" : ""}`}
                    >
                      {conv.unread_count}
                    </span>
                  )}
                </span>
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
