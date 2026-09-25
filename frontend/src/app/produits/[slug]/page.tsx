import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/Feedback";
import { ProductGallery } from "@/components/product/ProductGallery";
import { ContactSupplierCard } from "@/components/product/ContactSupplierCard";
import { ShareButton } from "@/components/product/ShareButton";
import { FavoriteButton } from "@/components/product/FavoriteButton";
import { getProduct } from "@/lib/api";
import { ApiError } from "@/lib/server-api";
import { formatDate, formatPrice, rentalPeriodLabel } from "@/lib/format";
import type { ProductAttribute } from "@/lib/types";

function formatAttributeValue(attribute: ProductAttribute) {
  const { value, unit } = attribute;
  if (typeof value === "boolean") return value ? "Oui" : "Non";
  const text = Array.isArray(value) ? value.join(", ") : String(value);
  return unit ? `${text} ${unit}` : text;
}

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: PageProps<"/produits/[slug]">) {
  const { slug } = await params;
  try {
    const product = await getProduct(slug);
    return {
      title: product.title,
      description: product.description.slice(0, 160),
      alternates: { canonical: `/produits/${slug}` },
      openGraph: {
        title: product.title,
        description: product.description.slice(0, 160),
        images: product.cover_image ? [product.cover_image] : [],
        url: `/produits/${slug}`,
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title: product.title,
        description: product.description.slice(0, 160),
        images: product.cover_image ? [product.cover_image] : [],
      },
    };
  } catch {
    return { title: "Article" };
  }
}

export default async function ProductDetailPage({ params }: PageProps<"/produits/[slug]">) {
  const { slug } = await params;

  let product;
  try {
    product = await getProduct(slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ProductGallery images={product.images} title={product.title} />

          <div className="mt-6 flex items-start justify-between gap-4">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Badge tone={product.listing_type === "rent" ? "brand" : "warning"}>
                  {product.listing_type === "rent" ? "Location" : "Vente"}
                </Badge>
                {product.category && <Badge>{product.category.name}</Badge>}
              </div>
              <h1 className="text-2xl font-bold">{product.title}</h1>
              <p className="mt-1 text-sm text-foreground-muted">
                {product.city} · Publié le {product.published_at ? formatDate(product.published_at) : formatDate(product.created_at)}
              </p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
              <FavoriteButton slug={product.slug} initial={product.is_favorite} variant="button" />
              <ShareButton slug={product.slug} title={product.title} price={product.price} currency={product.currency} city={product.city} />
            </div>
          </div>

          <p className="mt-4 text-2xl font-semibold text-brand-dark">
            {formatPrice(product.price, product.currency)}
            {product.listing_type === "rent" && (
              <span className="text-base font-normal text-foreground-muted"> / {rentalPeriodLabel(product.rental_period)}</span>
            )}
          </p>

          <div className="mt-6 border-t border-border pt-6">
            <h2 className="mb-2 text-base font-semibold">Description</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-foreground-muted">
              {product.description || "Aucune description fournie."}
            </p>
          </div>

          {product.attributes.length > 0 && (
            <div className="mt-6 border-t border-border pt-6">
              <h2 className="mb-3 text-base font-semibold">Caractéristiques</h2>
              <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
                {product.attributes.map((attribute) => (
                  <div
                    key={attribute.slug}
                    className="flex items-baseline justify-between gap-3 border-b border-border py-1.5"
                  >
                    <dt className="text-sm text-foreground-muted">{attribute.name}</dt>
                    <dd className="text-sm font-medium text-foreground">
                      {formatAttributeValue(attribute)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          <div className="mt-6 border-t border-border pt-6">
            <h2 className="mb-2 text-base font-semibold">Localisation</h2>
            <p className="text-sm text-foreground-muted">
              {[product.location, product.city, product.region, product.country].filter(Boolean).join(", ")}
            </p>
            {product.map_url && (
              <a
                href={product.map_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-brand-700 underline underline-offset-2"
              >
                Voir sur Google Maps →
              </a>
            )}
          </div>
        </div>

        <div className="lg:sticky lg:top-20 lg:h-fit">
          <ContactSupplierCard slug={product.slug} productId={product.id} supplier={product.supplier} productTitle={product.title} />
        </div>
      </div>
    </div>
  );
}
