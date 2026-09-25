"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { useAuth, RegisterError } from "@/components/providers/AuthProvider";

const schema = z
  .object({
    phone: z.string().min(8, "Numéro invalide"),
    first_name: z.string().min(1, "Prénom requis"),
    last_name: z.string().min(1, "Nom requis"),
    role: z.enum(["visitor", "supplier"]),
    password: z.string().min(8, "8 caractères minimum"),
    password2: z.string(),
  })
  .refine((data) => data.password === data.password2, {
    message: "Les mots de passe ne correspondent pas",
    path: ["password2"],
  });

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: signUp } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { role: "visitor" } });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await signUp(values);
      router.push("/login");
    } catch (err) {
      if (err instanceof RegisterError) {
        for (const [field, messages] of Object.entries(err.fields)) {
          if (field in values) {
            setError(field as keyof FormValues, { message: messages.join(" ") });
          }
        }
        if (!("phone" in err.fields) && !("password" in err.fields)) {
          setServerError(Object.values(err.fields).flat().join(" ") || "Inscription impossible.");
        }
      } else {
        setServerError("Inscription impossible pour le moment.");
      }
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold">Créer un compte</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <Select label="Je suis..." {...register("role")}>
          <option value="visitor">Un particulier qui cherche à louer/acheter</option>
          <option value="supplier">Un fournisseur qui veut publier des articles</option>
        </Select>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Prénom" {...register("first_name")} error={errors.first_name?.message} />
          <Input label="Nom" {...register("last_name")} error={errors.last_name?.message} />
        </div>
        <Input label="Téléphone" placeholder="+226 70 00 00 00" {...register("phone")} error={errors.phone?.message} />
        <Input label="Mot de passe" type="password" {...register("password")} error={errors.password?.message} />
        <Input label="Confirmer le mot de passe" type="password" {...register("password2")} error={errors.password2?.message} />
        {serverError && (
          <p role="alert" className="text-sm text-danger-fg">
            {serverError}
          </p>
        )}
        <Button type="submit" disabled={isSubmitting} className="mt-2">
          {isSubmitting ? "Création..." : "Créer mon compte"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-foreground-muted">
        Déjà inscrit ?{" "}
        <Link href="/login" className="font-medium text-brand-dark">
          Se connecter
        </Link>
      </p>
    </div>
  );
}
