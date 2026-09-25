"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { AudioMessage } from "./AudioMessage";
import { apiFetchBlob } from "@/lib/client-api";
import { formatDuration } from "@/lib/format";
import type { MessageAttachment } from "@/lib/types";

/**
 * The media inside one message bubble.
 *
 * Everything here is fetched with the access token and shown from an object
 * URL: the endpoints are participant-only, and a plain `<img src>` or
 * `<video src>` sends no Authorization header.
 *
 * Nothing loads until it is close to the screen, and a video only ever
 * downloads its poster until someone presses play — scrolling back through a
 * long conversation must not pull down every clip ever sent.
 */
export function AttachmentGallery({
  attachments,
  mine,
}: {
  attachments: MessageAttachment[];
  mine: boolean;
}) {
  if (attachments.length === 0) return null;

  const images = attachments.filter((a) => a.kind === "image");
  const videos = attachments.filter((a) => a.kind === "video");
  const audios = attachments.filter((a) => a.kind === "audio");

  return (
    <div className="flex flex-col gap-2">
      {images.length > 0 && (
        <div
          className={clsx(
            "grid gap-1",
            images.length === 1 ? "grid-cols-1" : "grid-cols-2"
          )}
        >
          {images.map((attachment) => (
            <ImageAttachment key={attachment.id} attachment={attachment} single={images.length === 1} />
          ))}
        </div>
      )}
      {videos.map((attachment) => (
        <VideoAttachment key={attachment.id} attachment={attachment} />
      ))}
      {audios.map((attachment) => (
        <AudioMessage
          key={attachment.id}
          src={attachment.url}
          duration={attachment.duration}
          mine={mine}
        />
      ))}
    </div>
  );
}

/** Loads `src` through the API once the element is near the viewport. */
function useAuthedMedia(src: string | null, { eager = false } = {}) {
  const ref = useRef<HTMLDivElement>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [visible, setVisible] = useState(eager);

  // `eager` can flip after the first render (pressing play on a video), and
  // `useState(eager)` only reads it once — without this the fetch below
  // would wait for an intersection that never comes.
  useEffect(() => {
    if (eager) setVisible(true);
  }, [eager]);

  useEffect(() => {
    if (eager || visible || !ref.current) return;
    // IntersectionObserver is missing in jsdom and in older browsers; there,
    // load immediately rather than showing nothing at all.
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [eager, visible]);

  useEffect(() => {
    if (!visible || !src || objectUrl) return;
    let cancelled = false;
    let created: string | null = null;

    apiFetchBlob(src)
      .then((blob) => {
        if (cancelled) return;
        created = URL.createObjectURL(blob);
        setObjectUrl(created);
      })
      .catch(() => !cancelled && setFailed(true));

    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [visible, src, objectUrl]);

  return { ref, objectUrl, failed };
}

function ImageAttachment({ attachment, single }: { attachment: MessageAttachment; single: boolean }) {
  // The thumbnail is enough for the bubble; the full rendition is fetched
  // only when someone opens it.
  const { ref, objectUrl, failed } = useAuthedMedia(attachment.poster_url ?? attachment.url);
  const [open, setOpen] = useState(false);

  return (
    <>
      <div ref={ref} className={clsx("overflow-hidden rounded-lg bg-black/5", single ? "max-w-[280px]" : "")}>
        {failed ? (
          <p className="p-3 text-xs text-danger-fg" role="alert">
            Image indisponible.
          </p>
        ) : objectUrl ? (
          <button type="button" onClick={() => setOpen(true)} className="block w-full">
            {/* eslint-disable-next-line @next/next/no-img-element -- blob: URL from an authenticated fetch, not an optimisable remote image */}
            <img
              src={objectUrl}
              alt="Image envoyée dans la conversation"
              width={attachment.width || undefined}
              height={attachment.height || undefined}
              className="h-full w-full object-cover"
            />
          </button>
        ) : (
          <div
            className="w-full animate-pulse bg-black/10"
            style={{ aspectRatio: attachment.width && attachment.height ? `${attachment.width}/${attachment.height}` : "4/3" }}
          />
        )}
      </div>
      {open && <Lightbox attachment={attachment} onClose={() => setOpen(false)} />}
    </>
  );
}

function Lightbox({ attachment, onClose }: { attachment: MessageAttachment; onClose: () => void }) {
  const { objectUrl, failed } = useAuthedMedia(attachment.url, { eager: true });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Image en grand"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
    >
      {failed ? (
        <p className="text-white">Image indisponible.</p>
      ) : objectUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- blob: URL, see above
        <img src={objectUrl} alt="" className="max-h-full max-w-full rounded-lg object-contain" />
      ) : (
        <p className="text-white">Chargement…</p>
      )}
      <button
        type="button"
        onClick={onClose}
        aria-label="Fermer"
        className="absolute right-4 top-4 rounded-full bg-white/20 px-3 py-1 text-white"
      >
        ✕
      </button>
    </div>
  );
}

function VideoAttachment({ attachment }: { attachment: MessageAttachment }) {
  const poster = useAuthedMedia(attachment.poster_url);
  const [playing, setPlaying] = useState(false);
  const video = useAuthedMedia(playing ? attachment.url : null, { eager: playing });

  if (playing && video.objectUrl) {
    return (
      <video
        src={video.objectUrl}
        controls
        autoPlay
        playsInline
        className="max-h-[420px] w-full max-w-[280px] rounded-lg bg-black"
      />
    );
  }

  return (
    <button
      type="button"
      ref={poster.ref as unknown as React.Ref<HTMLButtonElement>}
      onClick={() => setPlaying(true)}
      aria-label="Lire la vidéo"
      className="relative block w-full max-w-[280px] overflow-hidden rounded-lg bg-black/70"
      style={{ aspectRatio: "16/9" }}
    >
      {poster.objectUrl && (
        // eslint-disable-next-line @next/next/no-img-element -- blob: URL, see above
        <img src={poster.objectUrl} alt="" className="h-full w-full object-cover opacity-90" />
      )}
      <span className="absolute inset-0 flex items-center justify-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-xl text-brand-800">
          ▶
        </span>
      </span>
      {attachment.duration > 0 && (
        <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
          {formatDuration(attachment.duration)}
        </span>
      )}
      {playing && !video.objectUrl && (
        <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[11px] text-white">
          Chargement…
        </span>
      )}
    </button>
  );
}
