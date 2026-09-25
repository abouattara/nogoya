"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useState } from "react";
import { Badge } from "@/components/ui/Feedback";
import { apiFetch } from "@/lib/client-api";
import type { ProductImage } from "@/lib/types";

/**
 * The editor pulls in the cropping library and a canvas pipeline that most
 * visits never touch, so it is fetched only when someone clicks "Modifier".
 */
const ImageEditor = dynamic(
  () => import("@/components/product/ImageEditor").then((m) => m.ImageEditor),
  { ssr: false, loading: () => <p className="text-sm text-foreground-muted">Chargement de l&apos;éditeur…</p> }
);


/**
 * Manages images already attached to a published product. Each action
 * (delete / set cover / reorder) applies immediately against the API —
 * there is no separate "save" step, so the annonce can never end up with a
 * half-applied, inconsistent image set (see ARCHITECTURE.md — "avoid
 * orphaned files / invalid references" from the image-editing addendum).
 */
export function ExistingImageManager({
  images,
  onChange,
}: {
  images: ProductImage[];
  onChange: (images: ProductImage[]) => void;
}) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ProductImage | null>(null);

  async function applyEdit(file: File) {
    if (!editing) return;
    setBusyId(editing.id);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("image", file);
      const updated = await apiFetch<ProductImage>(
        `/api/v1/product-images/${editing.id}/replace/`,
        { method: "POST", body: formData }
      );
      onChange(
        images.map((img) =>
          img.id === updated.id
            ? // cache-bust so the browser shows the retouched file, not the
              // previous one it already has under the same URL
              { ...updated, image: `${updated.image}?v=${Date.now()}` }
            : img
        )
      );
      setEditing(null);
    } catch {
      setError("La retouche n'a pas pu être enregistrée.");
    } finally {
      setBusyId(null);
    }
  }

  async function setCover(id: number) {
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/v1/product-images/${id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_cover: true }),
      });
      onChange(images.map((img) => ({ ...img, is_cover: img.id === id })));
    } catch {
      setError("Impossible de changer l'image principale.");
    } finally {
      setBusyId(null);
    }
  }

  async function remove(id: number) {
    if (!confirm("Supprimer cette image ?")) return;
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/api/v1/product-images/${id}/`, { method: "DELETE" });
      onChange(images.filter((img) => img.id !== id));
    } catch {
      setError("Impossible de supprimer cette image.");
    } finally {
      setBusyId(null);
    }
  }

  async function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= images.length) return;
    const reordered = [...images];
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    onChange(reordered);
    setError(null);
    try {
      await Promise.all(
        reordered.map((img, order) =>
          apiFetch(`/api/v1/product-images/${img.id}/`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order }),
          })
        )
      );
    } catch {
      setError("Le nouvel ordre n'a pas pu être enregistré.");
    }
  }

  if (images.length === 0) {
    return <p className="text-sm text-foreground-muted">Aucune image pour le moment.</p>;
  }

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {images.map((img, idx) => (
          <div key={img.id} className="relative w-28 overflow-hidden rounded-lg border border-border">
            <div className="relative aspect-square w-full bg-surface-muted">
              <Image src={img.image} alt="" fill className="object-cover" />
              {img.is_cover && (
                <span className="absolute left-1 top-1">
                  <Badge tone="brand">Principale</Badge>
                </span>
              )}
            </div>
            <div className="flex items-center justify-between gap-1 bg-surface p-1">
              <button
                type="button"
                onClick={() => move(idx, -1)}
                disabled={idx === 0 || busyId === img.id}
                className="rounded px-1 text-xs text-foreground-muted hover:bg-surface-muted disabled:opacity-30"
                aria-label="Déplacer vers la gauche"
              >
                ←
              </button>
              {!img.is_cover && (
                <button
                  type="button"
                  onClick={() => setCover(img.id)}
                  disabled={busyId === img.id}
                  className="text-xs text-brand-700 hover:underline"
                >
                  Principale
                </button>
              )}
              <button
                type="button"
                onClick={() => move(idx, 1)}
                disabled={idx === images.length - 1 || busyId === img.id}
                className="rounded px-1 text-xs text-foreground-muted hover:bg-surface-muted disabled:opacity-30"
                aria-label="Déplacer vers la droite"
              >
                →
              </button>
            </div>
            <button
              type="button"
              onClick={() => setEditing(img)}
              disabled={busyId === img.id}
              className="block w-full border-t border-border bg-surface py-1 text-xs text-brand-700 hover:bg-surface-muted"
            >
              ✎ Modifier
            </button>
            <button
              type="button"
              onClick={() => remove(img.id)}
              disabled={busyId === img.id}
              className="absolute right-1 top-1 rounded-full bg-foreground/70 px-1.5 text-xs text-white"
              aria-label="Supprimer cette image"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-danger-fg">{error}</p>}

      {editing && (
        <ImageEditor
          src={editing.image}
          fileName={`image-${editing.id}.jpg`}
          onCancel={() => setEditing(null)}
          onApply={applyEdit}
        />
      )}
    </div>
  );
}
