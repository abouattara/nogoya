"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { Avatar } from "@/components/messaging/Avatar";
import { MessageBubble } from "@/components/messaging/MessageBubble";
import { BackIcon, MicIcon, PaperclipIcon, SendIcon } from "@/components/messaging/ChatIcons";
import { MediaComposer, UploadProgress, type PendingMedia } from "@/components/messaging/MediaComposer";
import { AudioRecorder, type RecordedAudio } from "@/components/messaging/AudioRecorder";
import { apiFetch } from "@/lib/client-api";
import { uploadWithProgress, UploadError } from "@/lib/upload";
import { buildChatRows } from "@/lib/chat-rows";
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
  /** Le message déjà tapé, montré avant que le serveur l'ait confirmé. */
  const [echo, setEcho] = useState<string | null>(null);
  const [firstUnreadId, setFirstUnreadId] = useState<number | null>(null);

  const cancelUpload = useRef<(() => void) | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const stickToBottom = useRef(true);
  const unreadLocked = useRef(false);
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

  const messages = useMemo(() => messagesQuery.data?.results ?? [], [messagesQuery.data]);

  const myProductsQuery = useQuery({
    queryKey: ["my-products-picker"],
    queryFn: () => apiFetch<Paginated<ProductListItem>>("/api/v1/products/?mine=true"),
    enabled: showPicker && user?.role === "supplier",
  });

  // Où reprendre la lecture. Relevé une seule fois, et avant que l'appel
  // suivant ne marque tout comme lu : sinon le repère disparaîtrait au
  // moment précis où il devient utile.
  useEffect(() => {
    if (unreadLocked.current || !messagesQuery.data) return;
    unreadLocked.current = true;
    const first = messages.find((m) => !m.is_mine && !m.read_at && m.message_type !== "system");
    setFirstUnreadId(first ? first.id : null);
  }, [messagesQuery.data, messages]);

  useEffect(() => {
    apiFetch(`/api/v1/conversations/${conversationId}/read/`, { method: "POST" }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    });
  }, [conversationId, messages.length, queryClient]);

  // On suit le bas du fil, sauf si le lecteur est remonté : tirer la page
  // sous ses yeux pendant qu'il relit un ancien message est insupportable.
  useEffect(() => {
    const element = scrollRef.current;
    if (element && stickToBottom.current) element.scrollTop = element.scrollHeight;
  }, [messages.length, echo, progress]);

  const onScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    stickToBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 120;
  }, []);

  function growTextarea() {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 140)}px`;
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
      // On attend que la liste soit revenue avant de retirer l'écho :
      // l'effacer plus tôt ferait clignoter le message à l'envoi.
      await queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread"] });
    } finally {
      cancelUpload.current = null;
      setProgress(null);
    }
  }

  async function send() {
    const text = body.trim();
    if (!text && !attachedProduct && media.length === 0) return;
    setSending(true);
    setSendError(null);
    stickToBottom.current = true;

    const formData = new FormData();
    if (text) formData.append("body", body);
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

    // Le champ se vide tout de suite et le texte passe dans l'écho : on ne
    // retape pas un message parce que le réseau a mis deux secondes.
    setBody("");
    setEcho(text || null);
    requestAnimationFrame(growTextarea);

    try {
      await upload(formData);
      setAttachedProduct(null);
      setMedia([]);
    } catch (err) {
      // L'envoi a échoué : le texte revient dans le champ, il n'est pas perdu.
      setBody((current) => current || text);
      setSendError(err instanceof UploadError ? err.message : "Le message n'a pas pu être envoyé.");
    } finally {
      setEcho(null);
      setSending(false);
    }
  }

  async function sendAudio(audio: RecordedAudio) {
    setSending(true);
    setSendError(null);
    stickToBottom.current = true;
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

  if (conversationQuery.isLoading || messagesQuery.isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full flex-1" />
      </div>
    );
  }
  if (conversationQuery.isError || !conversationQuery.data) {
    return (
      <div className="p-4">
        <ErrorState message="Conversation introuvable." retry={() => conversationQuery.refetch()} />
      </div>
    );
  }

  const conversation = conversationQuery.data;
  const rows = buildChatRows(messages, firstUnreadId);
  const canSend = Boolean(body.trim()) || Boolean(attachedProduct) || media.length > 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center gap-3 border-b border-border px-3 py-2.5">
        <Link
          href="/compte/messages"
          aria-label="Revenir à la liste des conversations"
          className="rounded-lg p-1.5 text-foreground-muted hover:bg-surface-muted hover:text-foreground lg:hidden"
        >
          <BackIcon />
        </Link>
        <Avatar
          name={conversation.other_participant.full_name}
          src={conversation.other_participant.avatar}
          size={36}
        />
        <div className="min-w-0">
          <p className="truncate font-semibold leading-tight">
            {conversation.other_participant.full_name}
          </p>
          <p className="truncate text-xs text-foreground-muted">
            Toutes vos demandes tiennent dans ce fil.
          </p>
        </div>
      </header>

      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto overscroll-contain bg-surface-muted/40 px-3 py-4"
      >
        {rows.length === 0 && !echo ? (
          <p className="mx-auto mt-10 max-w-sm text-center text-sm text-foreground-muted">
            Écrivez votre premier message. L&apos;équipe vérifie la disponibilité
            auprès du fournisseur avant de vous mettre en relation.
          </p>
        ) : (
          <ul className="mx-auto flex w-full max-w-2xl flex-col">
            {rows.map((row) =>
              row.kind === "day" ? (
                <li key={row.key} className="my-3 flex justify-center">
                  <span className="rounded-full border border-border bg-surface px-3 py-0.5 text-[11px] font-medium text-foreground-muted">
                    {row.label}
                  </span>
                </li>
              ) : row.kind === "unread" ? (
                <li key={row.key} className="my-3 flex items-center gap-2">
                  <span aria-hidden="true" className="h-px flex-1 bg-accent-300" />
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-accent-600">
                    Nouveaux messages
                  </span>
                  <span aria-hidden="true" className="h-px flex-1 bg-accent-300" />
                </li>
              ) : (
                <MessageBubble
                  key={row.key}
                  message={row.message}
                  grouped={row.grouped}
                  endsGroup={row.endsGroup}
                />
              )
            )}
            {echo && (
              <li className="mt-3 flex items-end justify-end gap-2">
                <div className="flex max-w-[min(32rem,78%)] flex-col items-end">
                  <div className="rounded-2xl rounded-br-md bg-brand-600/70 px-3 py-2 text-sm text-white">
                    <p className="whitespace-pre-line break-words">{echo}</p>
                  </div>
                  <span className="mt-0.5 px-1 text-[11px] text-foreground-muted">Envoi…</span>
                </div>
              </li>
            )}
          </ul>
        )}
      </div>

      <div className="border-t border-border bg-surface px-3 py-2.5">
        {attachedProduct && (
          <div className="mb-2 flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-2 text-sm">
            <span className="truncate">Annonce jointe : {attachedProduct.title}</span>
            <button
              type="button"
              onClick={() => setAttachedProduct(null)}
              aria-label="Retirer l'annonce jointe"
              className="shrink-0 rounded px-1 text-foreground-muted hover:text-foreground"
            >
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

        {recording ? (
          <AudioRecorder onReady={sendAudio} onCancel={() => setRecording(false)} disabled={sending} />
        ) : (
          <>
            <MediaComposer items={media} onChange={setMedia} limit={6} disabled={sending} />
            <div className="flex items-end gap-1.5">
              {user?.role === "supplier" && (
                <IconButton
                  label="Joindre une annonce"
                  onClick={() => setShowPicker((v) => !v)}
                  pressed={showPicker}
                >
                  <PaperclipIcon />
                </IconButton>
              )}
              <IconButton
                label="Enregistrer un message vocal"
                onClick={() => setRecording(true)}
                disabled={sending}
              >
                <MicIcon />
              </IconButton>
              <textarea
                ref={textareaRef}
                value={body}
                onChange={(e) => {
                  setBody(e.target.value);
                  growTextarea();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={1}
                placeholder="Écrire un message…"
                aria-label="Votre message"
                className="max-h-36 flex-1 resize-none rounded-2xl border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-600"
              />
              {/* Rond plutot que le `Button` du design system : celui-ci
                  impose `rounded-lg` et un rembourrage de libelle, et le
                  surcharger par une classe concurrente dependrait de
                  l'ordre de la feuille de style, pas de l'intention. */}
              <button
                type="button"
                onClick={send}
                disabled={sending || !canSend}
                aria-label="Envoyer le message"
                title="Envoyer"
                className="shrink-0 rounded-full bg-brand-600 p-2.5 text-white transition-colors hover:bg-brand-700 active:bg-brand-800 disabled:pointer-events-none disabled:opacity-40"
              >
                <SendIcon className="h-5 w-5" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  disabled,
  pressed,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      className={clsx(
        "shrink-0 rounded-full p-2.5 transition-colors disabled:opacity-40",
        pressed ? "bg-brand-100 text-brand-800" : "text-foreground-muted hover:bg-surface-muted hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}
