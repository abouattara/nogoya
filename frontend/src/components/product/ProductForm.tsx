"use client";

import dynamic from "next/dynamic";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { apiFetch, ApiError } from "@/lib/client-api";
import { PRODUCT_PHOTO, formatBytes, prepareImage } from "@/lib/media-prep";
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

/**
 * Le poids de ce qui va partir.
 *
 * On ne parle de réduction que lorsqu'il y en a une : une photo déjà
 * légère est renvoyée telle quelle par `prepareImage`, et annoncer
 * « 123 Ko réduits à 123 Ko » donnait l'impression d'un calcul raté.
 */
function PhotoSummary({ photos }: { photos: NewPhoto[] }) {
  const before = photos.reduce((total, photo) => total + photo.originalSize, 0);
  const after = photos.reduce((total, photo) => total + photo.file.size, 0);
  const label = `${photos.length} photo${photos.length > 1 ? "s" : ""}`;

  return (
    <p className="mt-2 text-xs text-foreground-muted">
      {after < before
        ? `${label} — ${formatBytes(before)} réduits à ${formatBytes(after)} avant envoi.`
        : `${label} — ${formatBytes(after)} à envoyer.`}
    </p>
  );
}

/**
 * Les libellés des champs, pour que l'erreur dise de quoi elle parle.
 *
 * L'API répond `{"latitude": ["..."], "longitude": ["..."]}` ; aplatir les
 * valeurs donnait deux fois la même phrase sans jamais nommer le champ —
 * le vendeur lisait « Assurez-vous qu'il n'y a pas plus de 9 chiffres au
 * total » deux fois de suite, sans savoir où regarder.
 */
const FIELD_LABELS: Record<string, string> = {
  title: "Titre",
  category: "Catégorie",
  description: "Description",
  price: "Prix",
  currency: "Devise",
  listing_type: "Type d'offre",
  rental_period: "Période de location",
  city: "Ville",
  location: "Quartier",
  region: "Région",
  country: "Pays",
  latitude: "Latitude",
  longitude: "Longitude",
  location_precision: "Visibilité de la position",
  images: "Photos",
};

function formatFieldErrors(body: Record<string, unknown> | null): string {
  if (!body) return "";
  return Object.entries(body)
    .map(([field, value]) => {
      const text = (Array.isArray(value) ? value : [value]).map((m) => String(m)).join(" ");
      const label = FIELD_LABELS[field];
      // `detail` et `non_field_errors` ne désignent aucun champ : les
      // préfixer d'un nom inventé serait trompeur.
      return label ? `${label} : ${text}` : text;
    })
    .filter(Boolean)
    .join(" ");
}

/** Ce qu'on peut dire d'un échec, en une poignée de mots. */
function describeFailure(cause: unknown): string {
  if (!(cause instanceof ApiError)) return "connexion interrompue";
  const body = cause.body as Record<string, unknown> | null;
  // Sans corps JSON exploitable, la réponse vient d'un intermédiaire
  // (proxy, pare-feu applicatif) : le code est alors la seule information.
  return formatFieldErrors(body) || `erreur ${cause.status}`;
}

/**
 * Une photo choisie mais pas encore envoyée.
 *
 * L'URL de prévisualisation est gardée ici plutôt que fabriquée dans le
 * rendu : `URL.createObjectURL()` appelé pendant le rendu créait un blob à
 * chaque frappe au clavier, sans jamais le révoquer. Avec six photos, un
 * formulaire rempli au téléphone finissait par retenir des centaines de
 * copies des images en mémoire.
 */
interface NewPhoto {
  file: File;
  previewUrl: string;
  /** Taille du fichier sorti de l'appareil, avant compression locale. */
  originalSize: number;
}

export function ProductForm({ mode, product }: ProductFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [images, setImages] = useState<NewPhoto[]>([]);
  const [existingImages, setExistingImages] = useState(product?.images ?? []);
  const [preparing, setPreparing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [geoStatus, setGeoStatus] = useState<"idle" | "locating" | "done" | "denied">("idle");
  const [editingNewIndex, setEditingNewIndex] = useState<number | null>(null);
  const [attributeValues, setAttributeValues] = useState<AttributeValues>(() =>
    Object.fromEntries((product?.attributes ?? []).map((a) => [a.slug, a.value]))
  );
  const [attributeErrors, setAttributeErrors] = useState<Record<string, string>>({});

  // Les URL de prévisualisation sont révoquées en quittant la page : sans
  // cela, les octets des photos restent en mémoire jusqu'au rechargement.
  const previewUrls = useRef<string[]>([]);
  useEffect(() => {
    previewUrls.current = images.map((photo) => photo.previewUrl);
  }, [images]);
  useEffect(() => () => previewUrls.current.forEach(URL.revokeObjectURL), []);

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

  /**
   * Réduire les photos ici, avant l'envoi.
   *
   * Une photo de téléphone pèse 4 à 8 Mo pour 12 Mpx, alors que la plus
   * grande version conservée fait 1600 px. Les envoyer brutes, c'est faire
   * payer au vendeur un forfait data pour des pixels que le serveur jette —
   * et, sur un hébergement mutualisé où le redimensionnement se fait dans
   * la requête, c'est aussi ce qui la faisait échouer. Le chat procédait
   * déjà ainsi ; le formulaire d'annonce, non.
   */
  async function onFilesSelected(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setPreparing(true);
    try {
      const prepared = await Promise.all(
        Array.from(fileList).map(async (file) => {
          const { file: shrunk, previewUrl, originalSize } = await prepareImage(file, PRODUCT_PHOTO);
          return { file: shrunk, previewUrl, originalSize };
        })
      );
      setImages((prev) => [...prev, ...prepared]);
    } finally {
      setPreparing(false);
    }
  }

  function removeNewImage(idx: number) {
    setImages((prev) => {
      const gone = prev[idx];
      if (gone) URL.revokeObjectURL(gone.previewUrl);
      return prev.filter((_, i) => i !== idx);
    });
    setEditingNewIndex(null);
  }

  function replaceNewImage(index: number, file: File) {
    setImages((prev) =>
      prev.map((existing, i) => {
        if (i !== index) return existing;
        URL.revokeObjectURL(existing.previewUrl);
        return { file, previewUrl: URL.createObjectURL(file), originalSize: existing.originalSize };
      })
    );
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
        // Six décimales, pas quinze. `pos.coords.latitude` est un flottant
        // du navigateur : `12.371428299999999`. Le serveur n'en garde que
        // six — onze centimètres — et les chiffres suivants ne sont que du
        // bruit de représentation.
        setValue("latitude", pos.coords.latitude.toFixed(6));
        setValue("longitude", pos.coords.longitude.toFixed(6));
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

      // Une requête par photo, et non les six d'un bloc. Sur l'hébergement
      // mutualisé le redimensionnement se fait dans la requête : six photos
      // ensemble, c'est six fois la mémoire et la durée d'un coup, et le
      // worker se fait tuer — l'annonce était créée, mais sans aucune photo.
      // Séparées, chacune est une requête courte, et un échec n'emporte plus
      // que la photo concernée.
      const failed: string[] = [];
      for (const [index, photo] of images.entries()) {
        setUploadStatus(`Envoi de la photo ${index + 1} sur ${images.length}…`);
        const formData = new FormData();
        formData.append("images", photo.file);
        try {
          await apiFetch(`/api/v1/products/${saved.slug}/upload_images/`, {
            method: "POST",
            body: formData,
          });
        } catch (err) {
          // On continue : une photo refusée ne doit pas priver l'annonce
          // des suivantes. S'arrêter à la première laissait une galerie
          // vide alors que deux photos sur trois étaient parfaitement
          // envoyables.
          failed.push(`${index + 1} (${describeFailure(err)})`);
        }
      }
      setUploadStatus(null);

      if (failed.length) {
        await queryClient.invalidateQueries({ queryKey: ["my-products"] });
        const quelles = failed.length === 1 ? "la photo" : "les photos";
        setServerError(
          `L'annonce a bien été enregistrée${
            failed.length < images.length ? ` avec ${images.length - failed.length} photo(s)` : ""
          }, mais ${quelles} ${failed.join(", ")} n'a pas pu être envoyée. ` +
            `Ouvrez l'annonce depuis « Mes annonces » pour réessayer.`
        );
        return;
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
      setUploadStatus(null);
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
        // Sans corps JSON exploitable, l'erreur vient d'un intermédiaire
        // (proxy, pare-feu applicatif) et non de l'API : afficher le code
        // évite un message opaque impossible à diagnostiquer.
        setServerError(
          formatFieldErrors(body) || `Enregistrement impossible (erreur ${err.status}).`
        );
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
        {preparing && (
          <p className="mt-2 text-xs text-foreground-muted">Préparation des photos…</p>
        )}
        {images.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {images.map((photo, idx) => (
              <div key={photo.previewUrl} className="w-20 overflow-hidden rounded-lg border border-border">
                <div className="relative h-20 w-20">
                  <Image src={photo.previewUrl} alt="" fill className="object-cover" unoptimized />
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
        {images.length > 0 && <PhotoSummary photos={images} />}
      </div>

      {editingNewIndex !== null && images[editingNewIndex] && (
        <ImageEditor
          src={images[editingNewIndex].previewUrl}
          fileName={images[editingNewIndex].file.name}
          onCancel={() => setEditingNewIndex(null)}
          onApply={(file) => replaceNewImage(editingNewIndex, file)}
        />
      )}

      {serverError && (
        <p role="alert" className="text-sm text-danger-fg">
          {serverError}
        </p>
      )}

      {uploadStatus && (
        <p role="status" className="text-sm text-foreground-muted">
          {uploadStatus}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting || preparing} className="mt-2">
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
