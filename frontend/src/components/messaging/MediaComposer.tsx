"use client";

import { useEffect, useRef, useState } from "react";
import { formatBytes, prepareImage, prepareVideo } from "@/lib/media-prep";
import { formatDuration } from "@/lib/format";

export interface PendingMedia {
  id: string;
  kind: "image" | "video";
  file: File;
  poster: File | null;
  duration: number;
  previewUrl: string;
  originalSize: number;
}

const MAX_IMAGE_BYTES = 12 * 1024 * 1024;
const MAX_VIDEO_BYTES = 100 * 1024 * 1024;
const MAX_VIDEO_SECONDS = 60;

/**
 * Picks files, shrinks them, and shows what is about to be sent.
 *
 * Refusals happen here, before the upload: telling someone their video is
 * too long after two minutes of uploading is the worst possible moment. The
 * server enforces the same limits — this is courtesy, not security.
 */
export function MediaComposer({
  items,
  onChange,
  limit,
  disabled,
}: {
  items: PendingMedia[];
  onChange: (items: PendingMedia[]) => void;
  limit: number;
  disabled?: boolean;
}) {
  const imageInput = useRef<HTMLInputElement>(null);
  const videoInput = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [dragging, setDragging] = useState(false);

  // Object URLs are per-file allocations; releasing them on unmount keeps a
  // long chat session from holding every preview it ever made.
  useEffect(() => {
    return () => items.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addFiles(files: File[]) {
    if (files.length === 0) return;
    setError(null);

    const room = limit - items.length;
    if (room <= 0) {
      setError(`Vous pouvez joindre ${limit} fichiers au maximum.`);
      return;
    }

    setPreparing(true);
    const accepted: PendingMedia[] = [];
    for (const file of files.slice(0, room)) {
      const isImage = file.type.startsWith("image/");
      const isVideo = file.type.startsWith("video/");

      if (!isImage && !isVideo) {
        setError("Format non supporté : choisissez une image ou une vidéo.");
        continue;
      }
      if (isImage && file.size > MAX_IMAGE_BYTES) {
        setError(`« ${file.name} » dépasse ${formatBytes(MAX_IMAGE_BYTES)}.`);
        continue;
      }
      if (isVideo && file.size > MAX_VIDEO_BYTES) {
        setError(`« ${file.name} » dépasse ${formatBytes(MAX_VIDEO_BYTES)}.`);
        continue;
      }

      if (isImage) {
        const prepared = await prepareImage(file);
        accepted.push({
          id: crypto.randomUUID(),
          kind: "image",
          file: prepared.file,
          poster: null,
          duration: 0,
          previewUrl: prepared.previewUrl,
          originalSize: prepared.originalSize,
        });
      } else {
        const prepared = await prepareVideo(file);
        if (prepared.duration > MAX_VIDEO_SECONDS) {
          URL.revokeObjectURL(prepared.previewUrl);
          setError(`Les vidéos sont limitées à ${MAX_VIDEO_SECONDS} secondes.`);
          continue;
        }
        accepted.push({
          id: crypto.randomUUID(),
          kind: "video",
          file: prepared.file,
          poster: prepared.poster,
          duration: prepared.duration,
          previewUrl: prepared.previewUrl,
          originalSize: file.size,
        });
      }
    }
    setPreparing(false);
    if (accepted.length > 0) onChange([...items, ...accepted]);
  }

  function remove(id: string) {
    const item = items.find((candidate) => candidate.id === id);
    if (item) URL.revokeObjectURL(item.previewUrl);
    onChange(items.filter((candidate) => candidate.id !== id));
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        addFiles(Array.from(event.dataTransfer.files));
      }}
      className={dragging ? "rounded-lg ring-2 ring-brand-600" : undefined}
    >
      <input
        ref={imageInput}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(event) => {
          addFiles(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
      <input
        ref={videoInput}
        type="file"
        accept="video/*"
        hidden
        onChange={(event) => {
          addFiles(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />

      {error && (
        <p role="alert" className="mb-2 text-sm text-danger-fg">
          {error}
        </p>
      )}

      {items.length > 0 && (
        <ul className="mb-2 flex flex-wrap gap-2">
          {items.map((item) => (
            <li key={item.id} className="relative">
              <div className="h-20 w-20 overflow-hidden rounded-lg border border-border bg-surface-muted">
                {item.kind === "image" ? (
                  // eslint-disable-next-line @next/next/no-img-element -- local blob: preview
                  <img
                    src={item.previewUrl}
                    alt={`Aperçu de ${item.file.name}`}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <video src={item.previewUrl} muted playsInline className="h-full w-full object-cover" />
                )}
              </div>
              {item.kind === "video" && item.duration > 0 && (
                <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1 text-[10px] text-white">
                  {formatDuration(item.duration)}
                </span>
              )}
              <button
                type="button"
                onClick={() => remove(item.id)}
                aria-label="Retirer ce fichier"
                className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-foreground text-xs text-white"
              >
                ✕
              </button>
              {item.originalSize > item.file.size && (
                <span className="sr-only">
                  Compressée de {formatBytes(item.originalSize)} à {formatBytes(item.file.size)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => imageInput.current?.click()}
          disabled={disabled || preparing}
          aria-label="Ajouter une image"
          title="Ajouter une image"
          className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted disabled:opacity-50"
        >
          🖼️
        </button>
        <button
          type="button"
          onClick={() => videoInput.current?.click()}
          disabled={disabled || preparing}
          aria-label="Ajouter une vidéo"
          title="Ajouter une vidéo"
          className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted disabled:opacity-50"
        >
          🎥
        </button>
        {preparing && <span className="self-center text-xs text-foreground-muted">Préparation…</span>}
      </div>
    </div>
  );
}

/** Upload progress with a way out. */
export function UploadProgress({
  percent,
  onCancel,
}: {
  percent: number;
  onCancel: () => void;
}) {
  return (
    <div className="mb-2 flex items-center gap-3" role="status" aria-live="polite">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-muted">
        <div
          className="h-full bg-brand-600 transition-[width]"
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progression de l'envoi"
        />
      </div>
      <span className="text-xs tabular-nums text-foreground-muted">{percent}%</span>
      <button type="button" onClick={onCancel} className="text-xs text-danger-fg hover:underline">
        Annuler
      </button>
    </div>
  );
}
