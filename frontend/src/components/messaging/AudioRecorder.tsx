"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { formatDuration } from "@/lib/format";
import {
  RECORDER_ERROR_MESSAGES,
  classifyRecorderError,
  extensionForMimeType,
  isRecordingSupported,
  pickRecordingMimeType,
} from "@/lib/audio";

export interface RecordedAudio {
  file: File;
  duration: number;
  url: string;
}

type Phase = "idle" | "recording" | "paused" | "preview";

/**
 * Record → preview → send/discard, using the native MediaRecorder API.
 * The parent only receives the finished clip through `onReady`.
 */
export function AudioRecorder({
  onReady,
  onCancel,
  disabled,
}: {
  onReady: (audio: RecordedAudio) => void;
  onCancel?: () => void;
  disabled?: boolean;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<RecordedAudio | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const durationRef = useRef(0);

  function stopTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function releaseStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  // Never leave the mic light on if the component unmounts mid-recording.
  useEffect(() => {
    return () => {
      stopTimer();
      releaseStream();
      if (preview) URL.revokeObjectURL(preview.url);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startRecording() {
    setError(null);
    if (!isRecordingSupported()) {
      setError(RECORDER_ERROR_MESSAGES.unsupported);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = pickRecordingMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      durationRef.current = 0;
      setSeconds(0);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        releaseStream();
        if (blob.size === 0) {
          setPhase("idle");
          setError("Enregistrement vide, réessayez.");
          return;
        }
        const file = new File([blob], `vocal.${extensionForMimeType(type)}`, { type });
        const recorded = {
          file,
          duration: Math.max(1, durationRef.current),
          url: URL.createObjectURL(blob),
        };
        setPreview(recorded);
        setPhase("preview");
      };

      recorder.start();
      recorderRef.current = recorder;
      setPhase("recording");
      timerRef.current = setInterval(() => {
        durationRef.current += 1;
        setSeconds(durationRef.current);
      }, 1000);
    } catch (err) {
      releaseStream();
      setError(RECORDER_ERROR_MESSAGES[classifyRecorderError(err)]);
      setPhase("idle");
    }
  }

  function pauseRecording() {
    recorderRef.current?.pause();
    stopTimer();
    setPhase("paused");
  }

  function resumeRecording() {
    recorderRef.current?.resume();
    setPhase("recording");
    timerRef.current = setInterval(() => {
      durationRef.current += 1;
      setSeconds(durationRef.current);
    }, 1000);
  }

  function stopRecording() {
    stopTimer();
    recorderRef.current?.stop();
  }

  function discard() {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
    setSeconds(0);
    durationRef.current = 0;
    setPhase("idle");
    onCancel?.();
  }

  function send() {
    if (!preview) return;
    onReady(preview);
    setPreview(null);
    setSeconds(0);
    durationRef.current = 0;
    setPhase("idle");
  }

  if (phase === "idle") {
    return (
      <div className="flex flex-col gap-1">
        <button
          type="button"
          onClick={startRecording}
          disabled={disabled}
          aria-label="Enregistrer un message vocal"
          title="Enregistrer un message vocal"
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-border text-foreground hover:bg-surface-muted disabled:opacity-50"
        >
          🎙️
        </button>
        {error && (
          <p role="alert" className="text-xs text-danger-fg">
            {error}
          </p>
        )}
      </div>
    );
  }

  if (phase === "recording" || phase === "paused") {
    return (
      <div className="flex w-full items-center gap-3 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2">
        <span className="flex items-center gap-2 text-sm font-medium text-brand-800">
          <span
            className={`h-2.5 w-2.5 rounded-full bg-danger-600 ${phase === "recording" ? "animate-pulse" : ""}`}
            aria-hidden="true"
          />
          {phase === "recording" ? "Enregistrement" : "En pause"} · {formatDuration(seconds)}
        </span>
        <div className="ml-auto flex gap-2">
          {phase === "recording" ? (
            <Button type="button" variant="secondary" size="sm" onClick={pauseRecording}>
              Pause
            </Button>
          ) : (
            <Button type="button" variant="secondary" size="sm" onClick={resumeRecording}>
              Reprendre
            </Button>
          )}
          <Button type="button" size="sm" onClick={stopRecording}>
            ⏹ Arrêter
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={discard}>
            Annuler
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-wrap items-center gap-3 rounded-lg border border-border bg-surface-muted px-3 py-2">
      <audio controls src={preview?.url} className="h-9 max-w-[220px] flex-1" aria-label="Écouter le vocal" />
      <span className="text-sm text-foreground-muted">{formatDuration(preview?.duration ?? 0)}</span>
      <div className="ml-auto flex gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={discard} aria-label="Supprimer le vocal">
          🗑 Supprimer
        </Button>
        <Button type="button" size="sm" onClick={send}>
          Envoyer
        </Button>
      </div>
    </div>
  );
}
