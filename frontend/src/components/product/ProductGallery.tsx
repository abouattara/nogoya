"use client";

import Image from "next/image";
import { useState } from "react";
import clsx from "clsx";
import type { ProductImage } from "@/lib/types";

export function ProductGallery({ images, title }: { images: ProductImage[]; title: string }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);

  if (images.length === 0) {
    return <div className="flex aspect-4/3 items-center justify-center rounded-xl bg-surface-muted text-foreground-muted">Pas de photo</div>;
  }

  const active = images[activeIndex];

  return (
    <div>
      <button
        type="button"
        onClick={() => setFullscreen(true)}
        className="relative block aspect-4/3 w-full overflow-hidden rounded-xl bg-surface-muted"
      >
        <Image src={active.image} alt={title} fill sizes="(max-width: 768px) 100vw, 50vw" className="object-cover" priority />
      </button>

      {images.length > 1 && (
        <div className="mt-3 flex gap-2 overflow-x-auto">
          {images.map((img, idx) => (
            <button
              key={img.id}
              onClick={() => setActiveIndex(idx)}
              className={clsx(
                "relative h-16 w-20 shrink-0 overflow-hidden rounded-lg border-2",
                idx === activeIndex ? "border-brand" : "border-transparent opacity-70"
              )}
            >
              <Image src={img.image} alt="" fill sizes="80px" className="object-cover" />
            </button>
          ))}
        </div>
      )}

      {fullscreen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => setFullscreen(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="relative h-full max-h-[90vh] w-full max-w-4xl">
            <Image src={active.image} alt={title} fill sizes="100vw" className="object-contain" />
          </div>
          <button
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
            onClick={() => setFullscreen(false)}
            aria-label="Fermer"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
