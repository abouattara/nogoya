"use client";

import { useCallback, useEffect, useState } from "react";
import Cropper from "react-easy-crop";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Feedback";
import { ASPECT_PRESETS, renderEditedImage, type CropArea } from "@/lib/image-editing";

interface ImageEditorProps {
  src: string;
  fileName?: string;
  onCancel: () => void;
  onApply: (file: File) => Promise<void> | void;
}

/**
 * Crop / rotate / flip / zoom, applied in-browser through a canvas.
 * Works both before upload (new image) and on an already-published one.
 */
export function ImageEditor({ src, fileName = "image.jpg", onCancel, onApply }: ImageEditorProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [aspect, setAspect] = useState<number | undefined>(undefined);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [pixels, setPixels] = useState<CropArea | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onCropComplete = useCallback((_: CropArea, croppedAreaPixels: CropArea) => {
    setPixels(croppedAreaPixels);
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  async function apply() {
    if (!pixels) return;
    setSaving(true);
    setError(null);
    try {
      const file = await renderEditedImage(
        src,
        { crop: pixels, rotation, flipHorizontal: flipH, flipVertical: flipV },
        fileName
      );
      await onApply(file);
    } catch {
      setError("La retouche n'a pas pu être appliquée.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Éditeur d'image"
    >
      <div className="flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-surface">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-base font-semibold">Retoucher l&apos;image</h2>
          <button
            onClick={onCancel}
            aria-label="Fermer l'éditeur"
            className="rounded-lg px-2 py-1 text-foreground-muted hover:bg-surface-muted hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <div className="relative h-72 w-full bg-foreground/90 sm:h-96">
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            rotation={rotation}
            aspect={aspect}
            transform={[
              `translate(${crop.x}px, ${crop.y}px)`,
              `rotateZ(${rotation}deg)`,
              `rotateY(${flipH ? 180 : 0}deg)`,
              `rotateX(${flipV ? 180 : 0}deg)`,
              `scale(${zoom})`,
            ].join(" ")}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onRotationChange={setRotation}
            onCropComplete={onCropComplete}
          />
        </div>

        <div className="flex flex-col gap-4 overflow-y-auto p-4">
          <div>
            <p className="mb-2 text-xs font-medium text-foreground-muted">Format</p>
            <div className="flex flex-wrap gap-2">
              {ASPECT_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => setAspect(preset.value)}
                  aria-pressed={aspect === preset.value}
                  className={clsx(
                    "rounded-lg border px-3 py-1.5 text-sm transition-colors",
                    aspect === preset.value
                      ? "border-brand-300 bg-brand-50 font-medium text-brand-800"
                      : "border-border bg-surface text-foreground hover:bg-surface-muted"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex flex-col gap-1 text-xs font-medium text-foreground-muted">
            Zoom
            <input
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              aria-label="Zoom"
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-brand-200"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" size="sm" onClick={() => setRotation((r) => (r + 270) % 360)}>
              ↺ Tourner
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={() => setRotation((r) => (r + 90) % 360)}>
              ↻ Tourner
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setFlipH((v) => !v)}
              aria-pressed={flipH}
            >
              ⇆ Miroir horizontal
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setFlipV((v) => !v)}
              aria-pressed={flipV}
            >
              ⇅ Miroir vertical
            </Button>
          </div>

          {error && (
            <p role="alert" className="text-sm text-danger-fg">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
          <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
            Annuler
          </Button>
          <Button type="button" onClick={apply} disabled={saving || !pixels}>
            {saving ? <Spinner className="h-4 w-4" /> : "Valider la retouche"}
          </Button>
        </div>
      </div>
    </div>
  );
}
