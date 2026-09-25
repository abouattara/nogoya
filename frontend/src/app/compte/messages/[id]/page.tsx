"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { SharedProductCard } from "@/components/messaging/SharedProductCard";
import { AttachmentGallery } from "@/components/messaging/AttachmentGallery";
import { MediaComposer, UploadProgress, type PendingMedia } from "@/components/messaging/MediaComposer";
import { AudioRecorder, type RecordedAudio } from "@/components/messaging/AudioRecorder";
import { apiFetch } from "@/lib/client-api";
import { uploadWithProgress, UploadError } from "@/lib/upload";
import { formatDate } from "@/lib/format";
import { useAuthStore } from "@/store/auth-store";
import type { ConversationSummary, Message as ChatMessage, Paginated, ProductListItem } from "@/lib/types";

export default function ConversationPage({ params }: PageProps<"/compte/messages/[id]">) {
  const { id } = use(params);
  return (
    <RequireAuth>
      {() => <Thread conversationId={id} />}
    </RequireAuth>
  );
}

function Thread({ conversationId }: { conversationId: string }) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [attachedProduct, setAttachedProduct] = useState<ProductListItem | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [media, setMedia] = useState<PendingMedia[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const cancelUpload = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((s) => s.user);

  const conversationQuery = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => apiFetch<ConversationSummary>(`/api/v1/conversations/${conversationId}/`),
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => apiFetch<Paginated<ChatMessage>>(`/api/v1/conversations/${conversationId}/messages/`),
    refetchInterval: 4_000,
  });

  const myProductsQuery = useQuery({
    queryKey: ["my-products-picker"],
    queryFn: () => apiFetch<Paginated<ProductListItem>>("/api/v1/products/?mine=true"),
    enabled: showPicker && user?.role === "supplier",
  });

  useEffect(() => {
    apiFetch(`/api/v1/conversations/${conversationId}/read/`, { method: "POST" }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    });
  }, [conversationId, messagesQuery.data?.results.length, queryClient]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messagesQuery.data?.results.length]);

  async function send() {
    if (!body.trim() && !attachedProduct && media.length === 0) return;
    setSending(true);
    setSendError(null);

    const formData = new FormData();
    if (body.trim()) formData.append("body", body);
    if (attachedProduct) formData.append("shared_product", String(attachedProduct.id));
    for (const item of media) {
      if (item.kind === "image") {
        formData.append("images", item.file);
      } else {
        formData.append("videos", item.file);
        // Paired by order with `videos`; a video without a usable poster
        // still sends, it just shows a placeholder.
        if (item.poster) formData.append("posters", item.poster);
        formData.append("durations", String(item.duration));
      }
    }

    try {
      await upload(formData);
      setBody("");
      setAttachedProduct(null);
      setMedia([]);
    } catch (err) {
      setSendError(err instanceof UploadError ? err.message : "Le message n'a pas pu être envoyé.");
    } finally {
      setSending(false);
    }
  }

  async function sendAudio(audio: RecordedAudio) {
    setSending(true);
    setSendError(null);
    const formData = new FormData();
    formData.append("audios", audio.file);
    formData.append("durations", String(audio.duration));
    try {
      await upload(formData);
      setRecording(false);
    } catch (err) {
      setSendError(err instanceof UploadError ? err.message : "Le vocal n'a pas pu être envoyé.");
    } finally {
      setSending(false);
    }
  }

  /** One upload path for every kind of message, with progress and a cancel. */
  async function upload(formData: FormData) {
    setProgress(0);
    const handle = uploadWithProgress(
      `/api/v1/conversations/${conversationId}/messages/`,
      formData,
      setProgress
    );
    cancelUpload.current = handle.cancel;
    try {
      await handle.done;
      refreshThread();
    } finally {
      cancelUpload.current = null;
      setProgress(null);
    }
  }

  function refreshThread() {
    queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
  }

  if (conversationQuery.isLoading || messagesQuery.isLoading) return <Skeleton className="h-[70vh] w-full" />;
  if (conversationQuery.isError || !conversationQuery.data) {
    return <ErrorState message="Conversation introuvable." retry={() => conversationQuery.refetch()} />;
  }

  const conversation = conversationQuery.data;
  const messages = messagesQuery.data?.results ?? [];

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-2xl flex-col px-4 py-4 sm:px-6">
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <Link href="/compte/messages" className="text-sm text-brand-700">
          ←
        </Link>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-800">
          {conversation.other_participant.full_name.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <p className="font-medium">{conversation.other_participant.full_name}</p>
          {conversation.initial_product && (
            <Link href={`/produits/${conversation.initial_product.slug}`} className="text-xs text-foreground-muted hover:underline">
              à propos de « {conversation.initial_product.title} »
            </Link>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto py-4">
        {messages.map((msg) => (
          <div key={msg.id} className={clsx("flex flex-col", msg.is_mine ? "items-end" : "items-start")}>
            <div
              className={clsx(
                "max-w-[80%] rounded-2xl px-3 py-2 text-sm",
                msg.is_mine ? "bg-brand-600 text-white" : "bg-surface-muted text-foreground"
              )}
            >
              {msg.body && <p className="whitespace-pre-line">{msg.body}</p>}
              {msg.attachments.length > 0 && (
                <div className={msg.body ? "mt-2" : undefined}>
                  <AttachmentGallery attachments={msg.attachments} mine={msg.is_mine} />
                </div>
              )}
              {msg.shared_product && <SharedProductCard product={msg.shared_product} />}
            </div>
            <span className="mt-0.5 text-[11px] text-foreground-muted">{formatDate(msg.created_at)}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {attachedProduct && (
        <div className="mb-2 flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2 text-sm">
          <span>📎 {attachedProduct.title}</span>
          <button onClick={() => setAttachedProduct(null)} className="text-foreground-muted hover:text-foreground">
            ✕
          </button>
        </div>
      )}

      {showPicker && user?.role === "supplier" && (
        <div className="mb-2 max-h-40 overflow-y-auto rounded-lg border border-border">
          {myProductsQuery.data?.results.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setAttachedProduct(p);
                setShowPicker(false);
              }}
              className="block w-full px-3 py-2 text-left text-sm hover:bg-surface-muted"
            >
              {p.title}
            </button>
          ))}
          {myProductsQuery.data?.results.length === 0 && (
            <p className="px-3 py-2 text-sm text-foreground-muted">Aucune annonce à joindre.</p>
          )}
        </div>
      )}

      {sendError && (
        <p role="alert" className="mb-2 text-sm text-danger-fg">
          {sendError}
        </p>
      )}

      {progress !== null && (
        <UploadProgress percent={progress} onCancel={() => cancelUpload.current?.()} />
      )}

      {!recording && (
        <MediaComposer items={media} onChange={setMedia} limit={6} disabled={sending} />
      )}

      {recording ? (
        <div className="border-t border-border pt-3">
          <AudioRecorder onReady={sendAudio} onCancel={() => setRecording(false)} disabled={sending} />
        </div>
      ) : (
        <div className="flex items-end gap-2 border-t border-border pt-3">
          {user?.role === "supplier" && (
            <button
              type="button"
              onClick={() => setShowPicker((v) => !v)}
              className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted"
              aria-label="Joindre une annonce"
            >
              +
            </button>
          )}
          {user?.role !== "supplier" && conversation.initial_product && !attachedProduct && (
            <button
              type="button"
              onClick={() => setAttachedProduct(conversation.initial_product)}
              className="rounded-lg border border-border px-2 py-2 text-xs hover:bg-surface-muted"
            >
              📎 Joindre le produit
            </button>
          )}
          <button
            type="button"
            onClick={() => setRecording(true)}
            disabled={sending}
            aria-label="Enregistrer un message vocal"
            title="Enregistrer un message vocal"
            className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted disabled:opacity-50"
          >
            🎙️
          </button>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Écrire un message..."
            className="flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-600"
          />
          <Button
            onClick={send}
            disabled={sending || (!body.trim() && !attachedProduct && media.length === 0)}
          >
            Envoyer
          </Button>
        </div>
      )}
    </div>
  );
}
