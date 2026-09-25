"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/components/providers/AuthProvider";

const schema = z.object({
  phone: z.string().min(8, "Numéro invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values.phone, values.password);
      router.push("/compte");
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Connexion impossible.");
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold">Connexion</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <Input label="Téléphone" placeholder="+226 70 00 00 00" {...register("phone")} error={errors.phone?.message} />
        <Input label="Mot de passe" type="password" {...register("password")} error={errors.password?.message} />
        {serverError && (
          <p role="alert" className="text-sm text-danger-fg">
            {serverError}
          </p>
        )}
        <Button type="submit" disabled={isSubmitting} className="mt-2">
          {isSubmitting ? "Connexion..." : "Se connecter"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-foreground-muted">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-medium text-brand-dark">
          Créer un compte
        </Link>
      </p>
    </div>
  );
}
