"use client";

import dynamic from "next/dynamic";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/client-api";
import type { AttributeValue, Category, LocationPrecision, ProductDetail } from "@/lib/types";
import { ExistingImageManager } from "./ExistingImageManager";
import { DynamicAttributeFields, type AttributeValues } from "./DynamicAttributeFields";

/**
 * The editor pulls in the cropping library and a canvas pipeline that most
 * visits never touch, so it is fetched only when someone clicks "Modifier".
 */
const ImageEditor = dynamic(
  () => import("@/components/product/ImageEditor").then((m) => m.ImageEditor),
  { ssr: false, loading: () => <p className="text-sm text-foreground-muted">Chargement de l&apos;éditeur…</p> }
);


const schema = z.object({
  title: z.string().min(3, "Titre trop court"),
  category: z.coerce.number().min(1, "Choisissez une catégorie"),
  description: z.string().min(10, "Décrivez votre article (10 caractères minimum)"),
  price: z.coerce.number().positive("Le prix doit être positif"),
  currency: z.string().min(1),
  listing_type: z.enum(["rent", "sale"]),
  rental_period: z.enum(["hour", "day", "week", "month", "none"]),
  city: z.string().min(1, "Ville requise"),
  location: z.string().optional(),
  region: z.string().optional(),
  country: z.string().optional(),
  location_precision: z.enum(["exact", "approximate"]),
  latitude: z.string().optional(),
  longitude: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

function flattenCategories(categories: Category[], depth = 0): Array<{ id: number; name: string; depth: number; isLeaf: boolean }> {
  return categories.flatMap((cat) => [
    { id: cat.id, name: cat.name, depth, isLeaf: cat.children.length === 0 },
    ...flattenCategories(cat.children, depth + 1),
  ]);
}

function findCategory(categories: Category[], id: number): Category | undefined {
  for (const category of categories) {
    if (category.id === id) return category;
    const nested = findCategory(category.children, id);
    if (nested) return nested;
  }
  return undefined;
}

interface ProductFormProps {
  mode: "create" | "edit";
  product?: ProductDetail; // required for edit
}

export function ProductForm({ mode, product }: ProductFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [images, setImages] = useState<File[]>([]);
  const [existingImages, setExistingImages] = useState(product?.images ?? []);
  const [serverError, setServerError] = useState<string | null>(null);
  const [geoStatus, setGeoStatus] = useState<"idle" | "locating" | "done" | "denied">("idle");
  const [editingNewIndex, setEditingNewIndex] = useState<number | null>(null);
  const [attributeValues, setAttributeValues] = useState<AttributeValues>(() =>
    Object.fromEntries((product?.attributes ?? []).map((a) => [a.slug, a.value]))
  );
  const [attributeErrors, setAttributeErrors] = useState<Record<string, string>>({});

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<Category[]>("/api/v1/categories/", { auth: false }),
  });
  const flatCategories = categories ? flattenCategories(categories) : [];

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: product
      ? {
          title: product.title,
          category: product.category?.id,
          description: product.description,
          price: Number(product.price),
          currency: product.currency,
          listing_type: product.listing_type,
          rental_period: product.rental_period,
          city: product.city,
          location: product.location,
          region: product.region,
          country: product.country || "Burkina Faso",
          location_precision: product.location_precision,
          latitude: product.latitude != null ? String(product.latitude) : "",
          longitude: product.longitude != null ? String(product.longitude) : "",
        }
      : {
          currency: "XOF",
          listing_type: "rent",
          rental_period: "day",
          country: "Burkina Faso",
          location_precision: "approximate" as LocationPrecision,
        },
  });
  const listingType = watch("listing_type");
  const latitude = watch("latitude");
  const longitude = watch("longitude");
  const selectedCategoryId = watch("category");

  // Attribute definitions come from the selected (leaf) category, which
  // already includes the ones inherited from its parent.
  const selectedCategory = findCategory(categories ?? [], Number(selectedCategoryId));
  const categoryAttributes = selectedCategory?.attributes ?? [];

  function setAttribute(slug: string, value: AttributeValue) {
    setAttributeValues((prev) => ({ ...prev, [slug]: value }));
    setAttributeErrors((prev) => {
      if (!prev[slug]) return prev;
      const next = { ...prev };
      delete next[slug];
      return next;
    });
  }

  function onFilesSelected(fileList: FileList | null) {
    if (!fileList) return;
    setImages((prev) => [...prev, ...Array.from(fileList)]);
  }

  function removeNewImage(idx: number) {
    setImages((prev) => prev.filter((_, i) => i !== idx));
    setEditingNewIndex(null);
  }

  function replaceNewImage(index: number, file: File) {
    setImages((prev) => prev.map((existing, i) => (i === index ? file : existing)));
    setEditingNewIndex(null);
  }

  function useCurrentPosition() {
    if (!navigator.geolocation) {
      setGeoStatus("denied");
      return;
    }
    setGeoStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setValue("latitude", String(pos.coords.latitude));
        setValue("longitude", String(pos.coords.longitude));
        setGeoStatus("done");
      },
      () => setGeoStatus("denied"),
      { enableHighAccuracy: false, timeout: 10_000 }
    );
  }

  async function onSubmit(values: FormValues) {
    setServerError(null);
    setAttributeErrors({});
    if (mode === "create" && images.length === 0) {
      setServerError("Ajoutez au moins une photo.");
      return;
    }
    // Only send attributes that belong to the selected category, dropping
    // leftovers from a category the supplier switched away from.
    const attributes = Object.fromEntries(
      categoryAttributes
        .map((attribute) => [attribute.slug, attributeValues[attribute.slug]] as const)
        .filter(([, value]) => value !== undefined && value !== "" && value !== null)
    );
    const payload = {
      ...values,
      latitude: values.latitude ? Number(values.latitude) : null,
      longitude: values.longitude ? Number(values.longitude) : null,
      attributes,
    };
    try {
      const url = mode === "create" ? "/api/v1/products/" : `/api/v1/products/${product!.slug}/`;
      const method = mode === "create" ? "POST" : "PATCH";
      const saved = await apiFetch<ProductDetail>(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (images.length > 0) {
        const formData = new FormData();
        images.forEach((file) => formData.append("images", file));
        await apiFetch(`/api/v1/products/${saved.slug}/upload_images/`, {
          method: "POST",
          body: formData,
        });
      }

      // The dashboard lists are cached for 30s; without this the supplier
      // lands back on a table still showing what they just changed.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["my-products"] }),
        queryClient.invalidateQueries({ queryKey: ["supplier-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["product", saved.slug] }),
      ]);
      router.push("/compte/fournisseur");
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as Record<string, unknown> | null;
        // The API reports attribute problems as {attributes: {slug: msg}} —
        // surface them next to the field instead of in one opaque banner.
        const attributeIssues = body?.attributes;
        if (attributeIssues && typeof attributeIssues === "object" && !Array.isArray(attributeIssues)) {
          setAttributeErrors(
            Object.fromEntries(
              Object.entries(attributeIssues as Record<string, unknown>).map(([slug, message]) => [
                slug,
                Array.isArray(message) ? message.join(" ") : String(message),
              ])
            )
          );
          setServerError("Vérifiez les caractéristiques de l'annonce.");
          return;
        }
        const messages = body
          ? Object.values(body)
              .flat()
              .map((m) => String(m))
              .join(" ")
          : "";
        // Sans corps JSON exploitable, l'erreur vient d'un intermédiaire
        // (proxy, pare-feu applicatif) et non de l'API : afficher le code
        // évite un message opaque impossible à diagnostiquer.
        setServerError(messages || `Enregistrement impossible (erreur ${err.status}).`);
      } else {
        setServerError("Enregistrement impossible pour le moment.");
      }
    }
  }

  const mapPreviewUrl =
    latitude && longitude ? `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}` : null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
      <Input label="Titre de l'annonce" placeholder="Ex : Tente de réception 10x5m" {...register("title")} error={errors.title?.message} />

      <Controller
        control={control}
        name="category"
        render={({ field }) => (
          <Select
            label="Catégorie"
            value={String(field.value ?? "")}
            onChange={(e) => field.onChange(e.target.value)}
            onBlur={field.onBlur}
            error={errors.category?.message}
          >
            <option value="">— Choisir —</option>
            {flatCategories.map((cat) => (
              <option key={cat.id} value={cat.id} disabled={!cat.isLeaf}>
                {"  ".repeat(cat.depth)}
                {cat.name}
                {!cat.isLeaf ? " (choisir une sous-catégorie)" : ""}
              </option>
            ))}
          </Select>
        )}
      />

      <Textarea label="Description" rows={5} {...register("description")} error={errors.description?.message} />

      <div className="grid grid-cols-2 gap-3">
        <Select label="Type d'offre" {...register("listing_type")}>
          <option value="rent">Location</option>
          <option value="sale">Vente</option>
        </Select>
        {listingType === "rent" && (
          <Select label="Période" {...register("rental_period")}>
            <option value="hour">Par heure</option>
            <option value="day">Par jour</option>
            <option value="week">Par semaine</option>
            <option value="month">Par mois</option>
          </Select>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Input label="Prix" type="number" min={0} {...register("price")} error={errors.price?.message} />
        <Input label="Devise" {...register("currency")} error={errors.currency?.message} />
      </div>

      <DynamicAttributeFields
        attributes={categoryAttributes}
        values={attributeValues}
        errors={attributeErrors}
        onChange={setAttribute}
      />

      <fieldset className="flex flex-col gap-3 rounded-xl border border-border p-4">
        <legend className="px-1 text-sm font-semibold">Localisation</legend>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Ville" placeholder="Ouagadougou" {...register("city")} error={errors.city?.message} />
          <Input label="Région" placeholder="Centre" {...register("region")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Adresse / quartier (optionnel)" placeholder="Zone 1, secteur 15..." {...register("location")} />
          <Input label="Pays" {...register("country")} />
        </div>

        <div className="flex flex-col gap-2 rounded-lg bg-surface-muted p-3">
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" size="sm" onClick={useCurrentPosition} disabled={geoStatus === "locating"}>
              {geoStatus === "locating" ? "Localisation..." : "📍 Utiliser ma position actuelle"}
            </Button>
            {geoStatus === "done" && <span className="text-xs text-success-fg">Position détectée ✓</span>}
            {geoStatus === "denied" && (
              <span className="text-xs text-foreground-muted">Géolocalisation refusée — la saisie manuelle reste disponible.</span>
            )}
            {mapPreviewUrl && (
              <a href={mapPreviewUrl} target="_blank" rel="noreferrer" className="text-xs text-brand-700 underline underline-offset-2">
                Voir sur Google Maps
              </a>
            )}
          </div>
          <Select label="Visibilité de la position" {...register("location_precision")}>
            <option value="approximate">Position approximative (recommandé)</option>
            <option value="exact">Position exacte</option>
          </Select>
          <p className="text-xs text-foreground-muted">
            La position exacte n&apos;est jamais obligatoire : sans coordonnées, seule la ville sera affichée.
          </p>
        </div>
      </fieldset>

      <div>
        <label className="text-sm font-medium">Photos</label>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => onFilesSelected(e.target.files)}
          className="mt-1 block w-full text-sm"
        />
        {mode === "edit" && (
          <div className="mt-3">
            <p className="mb-2 text-xs font-medium text-foreground-muted">Images actuelles</p>
            <ExistingImageManager images={existingImages} onChange={setExistingImages} />
          </div>
        )}
        {images.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {images.map((file, idx) => (
              <div key={idx} className="w-20 overflow-hidden rounded-lg border border-border">
                <div className="relative h-20 w-20">
                  <Image src={URL.createObjectURL(file)} alt="" fill className="object-cover" unoptimized />
                  <button
                    type="button"
                    onClick={() => removeNewImage(idx)}
                    className="absolute right-0.5 top-0.5 rounded-full bg-foreground/70 px-1.5 text-xs text-white"
                    aria-label="Retirer cette photo"
                  >
                    ✕
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setEditingNewIndex(idx)}
                  className="block w-full border-t border-border bg-surface py-1 text-xs text-brand-700 hover:bg-surface-muted"
                >
                  ✎ Retoucher
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {editingNewIndex !== null && images[editingNewIndex] && (
        <ImageEditor
          src={URL.createObjectURL(images[editingNewIndex])}
          fileName={images[editingNewIndex].name}
          onCancel={() => setEditingNewIndex(null)}
          onApply={(file) => replaceNewImage(editingNewIndex, file)}
        />
      )}

      {serverError && (
        <p role="alert" className="text-sm text-danger-fg">
          {serverError}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting} className="mt-2">
        {isSubmitting ? "Enregistrement..." : mode === "create" ? "Publier l'annonce" : "Enregistrer les modifications"}
      </Button>
      <p className="text-xs text-foreground-muted">
        {mode === "create"
          ? "Votre annonce sera visible publiquement après validation par l'équipe de modération."
          : "Toute modification du contenu repasse l'annonce en attente de validation."}
      </p>
    </form>
  );
}
