"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorState, Skeleton } from "@/components/ui/Feedback";
import { RequireAuth } from "@/components/providers/RequireAuth";
import { DiscoverySections } from "@/components/discovery/DiscoverySections";
import { apiFetch } from "@/lib/client-api";
import type { Me } from "@/lib/types";

const schema = z.object({
  first_name: z.string().min(1, "Prénom requis"),
  last_name: z.string().min(1, "Nom requis"),
  email: z.union([z.literal(""), z.string().email("Email invalide")]),
});
type FormValues = z.infer<typeof schema>;

export default function AccountPage() {
  return (
    <RequireAuth>
      {(user) => (
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold">Mon compte</h1>
            <div className="flex flex-wrap gap-2">
              <ButtonLink href="/favoris" variant="secondary">
                Mes favoris
              </ButtonLink>
              {user.role === "supplier" && (
                <ButtonLink href="/compte/fournisseur">Tableau de bord fournisseur</ButtonLink>
              )}
            </div>
          </div>

          <div className="mb-10">
            <DiscoverySections />
          </div>

          <h2 className="mb-3 text-lg font-semibold">Mes informations</h2>
          <ProfileForm />
        </div>
      )}
    </RequireAuth>
  );
}

function ProfileForm() {
  const queryClient = useQueryClient();
  const { data: me, isLoading, isError, refetch } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<Me>("/api/v1/auth/me/"),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (me) reset({ first_name: me.first_name, last_name: me.last_name, email: me.email });
  }, [me, reset]);

  async function onSubmit(values: FormValues) {
    const updated = await apiFetch<Me>("/api/v1/auth/me/", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    queryClient.setQueryData(["me"], updated);
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (isError || !me) return <ErrorState message="Impossible de charger votre profil." retry={refetch} />;

  return (
    <div className="rounded-xl border border-border p-6">
      <p className="mb-4 text-sm text-foreground-muted">
        Téléphone : <span className="font-medium text-foreground">{me.phone}</span> (identifiant de connexion, non modifiable)
      </p>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Prénom" {...register("first_name")} error={errors.first_name?.message} />
          <Input label="Nom" {...register("last_name")} error={errors.last_name?.message} />
        </div>
        <Input label="Email" type="email" {...register("email")} error={errors.email?.message} />
        <Button type="submit" disabled={isSubmitting || !isDirty} className="w-fit">
          {isSubmitting ? "Enregistrement..." : "Enregistrer"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-foreground-muted">
        Envie de publier vos propres articles ?{" "}
        <Link href="/register" className="text-brand-dark underline underline-offset-2">
          Un compte fournisseur
        </Link>{" "}
        est nécessaire.
      </p>
    </div>
  );
}
