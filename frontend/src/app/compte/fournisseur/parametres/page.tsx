"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { apiFetch } from "@/lib/client-api";

interface SupplierMe {
  id: number;
  city: string;
  address: string;
  bio: string;
  whatsapp_number: string;
  allow_whatsapp_contact: boolean;
}

export default function SupplierSettingsPage() {
  return (
    <RequireAuth role="supplier">
      {() => (
        <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
          <h1 className="mb-6 text-2xl font-bold">Paramètres fournisseur</h1>
          <SettingsLoader />
        </div>
      )}
    </RequireAuth>
  );
}

function SettingsLoader() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["supplier-me"],
    queryFn: () => apiFetch<SupplierMe>("/api/v1/suppliers/me/"),
  });

  if (isLoading) return <Skeleton className="h-72 w-full" />;
  if (isError || !data) return <ErrorState message="Impossible de charger vos paramètres." retry={refetch} />;

  // Keyed on id so a fresh (uncontrolled-by-effect) local draft is created
  // once data is available, instead of syncing query state into local state
  // inside a useEffect.
  return <SettingsForm key={data.id} initial={data} />;
}

function SettingsForm({ initial }: { initial: SupplierMe }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initial);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await apiFetch<SupplierMe>("/api/v1/suppliers/me/", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city: form.city,
          address: form.address,
          bio: form.bio,
          whatsapp_number: form.whatsapp_number,
          allow_whatsapp_contact: form.allow_whatsapp_contact,
        }),
      });
      queryClient.setQueryData(["supplier-me"], updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border p-6">
      <Input label="Ville" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
      <Input label="Adresse" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      <Textarea label="Présentation" rows={4} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />

      <fieldset className="flex flex-col gap-3 rounded-lg bg-surface-muted p-4">
        <legend className="px-1 text-sm font-semibold">Contact WhatsApp</legend>
        <Input
          label="Numéro WhatsApp"
          placeholder="+226 70 00 00 00"
          value={form.whatsapp_number}
          onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })}
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.allow_whatsapp_contact}
            onChange={(e) => setForm({ ...form, allow_whatsapp_contact: e.target.checked })}
          />
          Autoriser les visiteurs à me contacter via WhatsApp
        </label>
        <p className="text-xs text-foreground-muted">
          Votre numéro de téléphone interne reste privé (visible uniquement via &quot;Afficher le
          contact&quot;, réservé aux utilisateurs connectés). Le numéro WhatsApp, si activé, est visible
          publiquement sur vos annonces.
        </p>
      </fieldset>

      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={saving} className="w-fit">
          {saving ? "Enregistrement..." : "Enregistrer"}
        </Button>
        {saved && <span className="text-sm text-success-fg">Enregistré ✓</span>}
      </div>
    </div>
  );
}
