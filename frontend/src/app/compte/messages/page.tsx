"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { Badge, EmptyState, ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";
import { formatDate } from "@/lib/format";
import type { ConversationSummary, Paginated } from "@/lib/types";

export default function MessagesPage() {
  return (
    <RequireAuth>
      {() => (
        <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Messages</h1>
          <ConversationList />
        </div>
      )}
    </RequireAuth>
  );
}

function ConversationList() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => apiFetch<Paginated<ConversationSummary>>("/api/v1/conversations/"),
    refetchInterval: 10_000,
  });

  if (isLoading) return <Skeleton className="h-72 w-full" />;
  if (isError || !data) return <ErrorState message="Impossible de charger vos messages." retry={refetch} />;
  if (data.results.length === 0) {
    return (
      <EmptyState
        title="Aucune conversation pour le moment"
        description="Contactez un fournisseur depuis une annonce pour démarrer une conversation."
      />
    );
  }

  return (
    <div className="flex flex-col divide-y divide-border overflow-hidden rounded-xl border border-border">
      {data.results.map((conv) => (
        <Link
          key={conv.id}
          href={`/compte/messages/${conv.id}`}
          className="flex items-center gap-3 p-4 hover:bg-surface-muted"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-800">
            {conv.other_participant.full_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate font-medium">{conv.other_participant.full_name}</p>
              {conv.last_message && (
                <span className="shrink-0 text-xs text-foreground-muted">{formatDate(conv.last_message.created_at)}</span>
              )}
            </div>
            {conv.initial_product && (
              <p className="truncate text-xs text-foreground-muted">à propos de « {conv.initial_product.title} »</p>
            )}
            <p className="truncate text-sm text-foreground-muted">
              {conv.last_message ? (conv.last_message.is_mine ? "Vous : " : "") + conv.last_message.body : "Nouvelle conversation"}
            </p>
          </div>
          {conv.initial_product?.cover_image && (
            <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-lg bg-surface-muted">
              <Image src={conv.initial_product.cover_image} alt="" fill className="object-cover" />
            </div>
          )}
          {conv.unread_count > 0 && <Badge tone="brand">{conv.unread_count}</Badge>}
        </Link>
      ))}
    </div>
  );
}
