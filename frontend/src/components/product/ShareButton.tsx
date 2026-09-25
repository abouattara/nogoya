"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/client-api";

interface ShareButtonProps {
  slug: string;
  title: string;
  price: string;
  currency: string;
  city: string;
}

function logShare(slug: string) {
  apiFetch(`/api/v1/products/${slug}/share/`, { method: "POST", auth: false }).catch(() => undefined);
}

export function ShareButton({ slug, title, price, currency, city }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        logShare(slug);
      } catch {
        // user cancelled the native share sheet — not a share, don't log it
      }
      return;
    }
    await navigator.clipboard.writeText(url);
    setCopied(true);
    logShare(slug);
    setTimeout(() => setCopied(false), 2000);
  }

  function shareWhatsApp() {
    const message = `${title} — ${price} ${currency} — ${city}\n${window.location.href}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, "_blank", "noopener");
    logShare(slug);
  }

  return (
    <div className="flex shrink-0 gap-2">
      <button
        onClick={shareWhatsApp}
        className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted"
        aria-label="Partager sur WhatsApp"
      >
        💬 WhatsApp
      </button>
      <button onClick={share} className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-surface-muted">
        {copied ? "Lien copié ✓" : "Partager"}
      </button>
    </div>
  );
}
