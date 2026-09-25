"use client";

/**
 * Shrinking media in the browser, before it ever leaves the device.
 *
 * On a phone in Ouagadougou, uploading a 6 MB photo over a slow connection
 * is the slowest part of sending a message — and it is money on both ends:
 * their data bundle, our bandwidth and storage. Re-encoding to something
 * closer to 250 KB first makes the send feel instant and costs nothing but a
 * canvas pass.
 *
 * No library: `createImageBitmap` + `<canvas>` do the resizing, and a
 * `<video>` element hands us the first frame as a poster. The server still
 * validates and re-encodes everything — this is an optimisation, never a
 * trust boundary.
 */

/** Longest edge kept for a chat photo. The server caps at 900px anyway. */
const MAX_EDGE = 1280;
const QUALITY = 0.82;

export interface PreparedImage {
  file: File;
  width: number;
  height: number;
  /** Local object URL for the preview; revoke it when done. */
  previewUrl: string;
  originalSize: number;
}

export interface PreparedVideo {
  file: File;
  poster: File | null;
  duration: number;
  previewUrl: string;
}

function canvasToFile(canvas: HTMLCanvasElement, name: string, quality = QUALITY): Promise<File> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("canvas-encode-failed"));
          return;
        }
        resolve(new File([blob], name, { type: "image/jpeg" }));
      },
      "image/jpeg",
      quality
    );
  });
}

/**
 * Downscale and re-encode one picture.
 *
 * Falls back to the untouched file when the browser cannot decode it (an
 * unusual HEIC, say): the server accepts those formats too, so the person
 * still gets their photo sent, just without the local saving.
 */
export async function prepareImage(file: File): Promise<PreparedImage> {
  const originalSize = file.size;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    const width = Math.round(bitmap.width * scale);
    const height = Math.round(bitmap.height * scale);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("no-2d-context");
    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close?.();

    const prepared = await canvasToFile(canvas, renameToJpeg(file.name));
    // Re-encoding a small, already-optimised picture can make it bigger.
    const best = prepared.size < file.size ? prepared : file;
    return { file: best, width, height, previewUrl: URL.createObjectURL(best), originalSize };
  } catch {
    return {
      file,
      width: 0,
      height: 0,
      previewUrl: URL.createObjectURL(file),
      originalSize,
    };
  }
}

function renameToJpeg(name: string) {
  const base = name.replace(/\.[^.]+$/, "") || "photo";
  return `${base}.jpg`;
}

/**
 * Read a video's duration and grab a still for its poster.
 *
 * The frame is taken client-side on purpose: the alternative is shipping
 * ffmpeg server-side to decode every upload just to show a thumbnail. The
 * poster is what makes a conversation scrollable without downloading
 * megabytes of video nobody asked to watch.
 */
export function prepareVideo(file: File): Promise<PreparedVideo> {
  return new Promise((resolve) => {
    const previewUrl = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.muted = true;
    video.playsInline = true;

    const giveUp = () => resolve({ file, poster: null, duration: 0, previewUrl });

    video.onerror = giveUp;
    video.onloadedmetadata = () => {
      const duration = Number.isFinite(video.duration) ? Math.round(video.duration) : 0;
      // Seek a little in: the very first frame is often black.
      video.currentTime = Math.min(0.5, Math.max(0, duration - 0.1));
      video.onseeked = async () => {
        try {
          const canvas = document.createElement("canvas");
          const scale = Math.min(1, MAX_EDGE / Math.max(video.videoWidth, video.videoHeight));
          canvas.width = Math.round(video.videoWidth * scale) || 320;
          canvas.height = Math.round(video.videoHeight * scale) || 180;
          const context = canvas.getContext("2d");
          if (!context) throw new Error("no-2d-context");
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          const poster = await canvasToFile(canvas, "poster.jpg", 0.7);
          resolve({ file, poster, duration, previewUrl });
        } catch {
          resolve({ file, poster: null, duration, previewUrl });
        }
      };
    };

    video.src = previewUrl;
  });
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
}
