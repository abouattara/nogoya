"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { apiFetchBlob } from "@/lib/client-api";
import { formatDuration } from "@/lib/format";

/**
 * Voice-message bubble: play/pause, scrubbing, duration, loading and error
 * states. Colours flip with `mine` so contrast stays correct on both the
 * violet (own message) and light (received) bubbles.
 *
 * The file is fetched with the access token and played from an object URL:
 * the endpoint is participant-only, and a plain `<audio src>` request would
 * carry no Authorization header. It downloads on first play, so opening a
 * long conversation does not pull every recording.
 */
export function AudioMessage({
  src,
  duration,
  mine = false,
}: {
  src: string;
  duration: number;
  mine?: boolean;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const objectUrlRef = useRef<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [position, setPosition] = useState(0);
  const [total, setTotal] = useState(duration || 0);

  // Drop the blob when the bubble goes away (and when the message changes).
  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTime = () => setPosition(audio.currentTime);
    const onLoaded = () => {
      setLoading(false);
      if (Number.isFinite(audio.duration) && audio.duration > 0) setTotal(audio.duration);
    };
    const onEnded = () => {
      setPlaying(false);
      setPosition(0);
    };
    const onError = () => {
      setError(true);
      setLoading(false);
      setPlaying(false);
    };

    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("loadedmetadata", onLoaded);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);
    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("loadedmetadata", onLoaded);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
    };
  }, []);

  async function toggle() {
    const audio = audioRef.current;
    if (!audio || error) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
      return;
    }
    try {
      setLoading(true);
      if (!objectUrlRef.current) {
        const blob = await apiFetchBlob(src);
        objectUrlRef.current = URL.createObjectURL(blob);
        audio.src = objectUrlRef.current;
      }
      await audio.play();
      setPlaying(true);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  /** Same reason as playback: the link needs the access token. */
  async function download() {
    try {
      if (!objectUrlRef.current) {
        const blob = await apiFetchBlob(src);
        objectUrlRef.current = URL.createObjectURL(blob);
      }
      const link = document.createElement("a");
      link.href = objectUrlRef.current;
      link.download = "message-vocal";
      link.click();
    } catch {
      setError(true);
    }
  }

  function seek(event: React.ChangeEvent<HTMLInputElement>) {
    const audio = audioRef.current;
    if (!audio) return;
    const next = Number(event.target.value);
    audio.currentTime = next;
    setPosition(next);
  }

  if (error) {
    return (
      <p className={clsx("text-xs", mine ? "text-white/80" : "text-danger-fg")} role="alert">
        Vocal indisponible.
      </p>
    );
  }

  return (
    <div className="flex min-w-[200px] items-center gap-3">
      <audio ref={audioRef} preload="none" />
      <button
        type="button"
        onClick={toggle}
        aria-label={playing ? "Mettre en pause" : "Écouter le message vocal"}
        className={clsx(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm",
          mine ? "bg-white/20 text-white hover:bg-white/30" : "bg-brand-600 text-white hover:bg-brand-700"
        )}
      >
        {loading ? "…" : playing ? "❚❚" : "▶"}
      </button>

      <div className="flex-1">
        <input
          type="range"
          min={0}
          max={total || duration || 1}
          step={0.1}
          value={Math.min(position, total || duration || 1)}
          onChange={seek}
          aria-label="Progression du vocal"
          className={clsx("h-1 w-full cursor-pointer appearance-none rounded-full", mine ? "bg-white/30" : "bg-brand-200")}
        />
        <span className={clsx("mt-1 block text-[11px]", mine ? "text-white/80" : "text-foreground-muted")}>
          {formatDuration(position)} / {formatDuration(total || duration)}
        </span>
      </div>

      <button
        type="button"
        onClick={download}
        aria-label="Télécharger le vocal"
        title="Télécharger"
        className={clsx("shrink-0 text-xs", mine ? "text-white/80 hover:text-white" : "text-foreground-muted hover:text-foreground")}
      >
        ⬇
      </button>
    </div>
  );
}
