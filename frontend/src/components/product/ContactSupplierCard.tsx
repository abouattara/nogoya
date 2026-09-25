"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Feedback";
import { apiFetch, ApiError } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import type { ConversationSummary, SupplierPublic } from "@/lib/types";

interface ContactSupplierCardProps {
  slug: string;
  productId: number;
  supplier: SupplierPublic;
  productTitle: string;
}

export function ContactSupplierCard({ slug, productId, supplier, productTitle }: ContactSupplierCardProps) {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const [phone, setPhone] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [messaging, setMessaging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startChat() {
    setMessaging(true);
    setError(null);
    try {
      const conversation = await apiFetch<ConversationSummary>("/api/v1/conversations/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product: productId }),
      });
      router.push(`/compte/messages/${conversation.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? "Impossible de démarrer la conversation." : "Erreur inattendue.");
    } finally {
      setMessaging(false);
    }
  }

  async function reveal() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ phone: string | null }>(`/api/v1/products/${slug}/contact/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "phone" }),
      });
      if (!data.phone) throw new Error("no-phone");
      setPhone(data.phone);
    } catch {
      setError("Impossible de récupérer le contact pour le moment.");
    } finally {
      setLoading(false);
    }
  }

  function openWhatsApp() {
    if (user) {
      apiFetch(`/api/v1/products/${slug}/contact/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "whatsapp" }),
      }).catch(() => undefined); // best-effort logging; never block the redirect
    }
    const message = `Bonjour, je suis intéressé(e) par "${productTitle}" sur nogoya.`;
    const number = (supplier.whatsapp_number ?? "").replace(/\D/g, "");
    window.open(`https://wa.me/${number}?text=${encodeURIComponent(message)}`, "_blank", "noopener");
  }

  return (
    <div className="rounded-xl border border-border p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-dark">
          {supplier.user.full_name.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <Link href={`/fournisseurs/${supplier.id}`} className="text-sm font-semibold hover:text-brand-dark">
            {supplier.user.full_name}
          </Link>
          <p className="text-xs text-foreground-muted">{supplier.city || "Localisation non précisée"}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2">
        {!user && (
          <div className="text-sm">
            <Link href="/login" className="text-brand-dark underline underline-offset-2">
              Connectez-vous
            </Link>{" "}
            pour afficher le contact du fournisseur.
          </div>
        )}
        {user && (
          <Button onClick={startChat} disabled={messaging} className="w-full">
            {messaging ? <Spinner className="h-4 w-4" /> : "💬 Envoyer un message"}
          </Button>
        )}
        {user && !phone && (
          <Button onClick={reveal} disabled={loading} variant="secondary" className="w-full">
            {loading ? <Spinner className="h-4 w-4" /> : "Afficher le contact"}
          </Button>
        )}
        {phone && (
          <a href={`tel:${phone}`} className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            📞 {phone}
          </a>
        )}
        {supplier.whatsapp_number && (
          <Button variant="secondary" onClick={openWhatsApp} className="w-full">
            💬 Contacter via WhatsApp
          </Button>
        )}
        {error && <p className="text-xs text-danger-fg">{error}</p>}
      </div>
    </div>
  );
}
