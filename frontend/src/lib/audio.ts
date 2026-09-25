/**
 * Browser audio-recording helpers.
 *
 * MediaRecorder support differs by browser: Chrome/Firefox/Edge produce
 * WebM/Opus, Safari (16.4+) only MP4/AAC. We therefore never hard-code a
 * mime type — we ask the browser what it can actually record and send that
 * to the server, which validates the real container bytes anyway.
 */

const CANDIDATE_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
  "audio/aac",
];

export function isRecordingSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia
  );
}

/** The first mime type this browser can actually record, or "" for its default. */
export function pickRecordingMimeType(): string {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") return "";
  for (const candidate of CANDIDATE_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return "";
}

/** ".webm" / ".mp4" ... derived from the negotiated mime type. */
export function extensionForMimeType(mimeType: string): string {
  const base = mimeType.split(";")[0];
  switch (base) {
    case "audio/mp4":
    case "audio/aac":
      return "m4a";
    case "audio/ogg":
      return "ogg";
    case "audio/mpeg":
      return "mp3";
    default:
      return "webm";
  }
}

export type RecorderErrorReason = "unsupported" | "permission-denied" | "no-device" | "unknown";

export function classifyRecorderError(error: unknown): RecorderErrorReason {
  if (!isRecordingSupported()) return "unsupported";
  const name = (error as DOMException)?.name;
  if (name === "NotAllowedError" || name === "SecurityError") return "permission-denied";
  if (name === "NotFoundError" || name === "DevicesNotFoundError") return "no-device";
  return "unknown";
}

export const RECORDER_ERROR_MESSAGES: Record<RecorderErrorReason, string> = {
  unsupported: "Votre navigateur ne permet pas l'enregistrement audio.",
  "permission-denied": "Accès au micro refusé. Autorisez le micro pour envoyer un vocal.",
  "no-device": "Aucun micro détecté sur cet appareil.",
  unknown: "Impossible de démarrer l'enregistrement.",
};
