import Link from "next/link";
import { ButtonLink } from "@/components/ui/Button";

// Marketplace listings change per request; never prerender stale data at build time.
export const dynamic = "force-dynamic";
import { SearchBar } from "@/components/search/SearchBar";
import { ProductGrid } from "@/components/product/ProductGrid";
import { getCategories, getProducts } from "@/lib/api";

export default async function HomePage() {
  const [categories, latest] = await Promise.all([
    getCategories(),
    getProducts({ ordering: "-created_at" }),
  ]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <section className="flex flex-col items-center gap-6 rounded-2xl bg-surface-muted px-6 py-14 text-center">
        <h1 className="max-w-2xl text-3xl font-bold sm:text-4xl">
          Louez ou achetez presque tout, directement auprès de particuliers et de professionnels
        </h1>
        <p className="max-w-xl text-foreground-muted">
          Véhicules, logements, équipements, outils, matériel événementiel... publiez ou trouvez
          votre prochain article en quelques clics.
        </p>
        <SearchBar />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold">Parcourir par catégorie</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {categories.map((cat) => (
            <Link
              key={cat.id}
              href={`/produits?category=${cat.slug}`}
              className="flex flex-col items-center gap-2 rounded-xl border border-border p-4 text-center text-sm font-medium transition-colors hover:border-brand hover:bg-brand-50"
            >
              <span>{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Publiés récemment</h2>
          <ButtonLink href="/produits" variant="ghost" size="sm">
            Voir tout →
          </ButtonLink>
        </div>
        <ProductGrid products={latest.results} />
      </section>
    </div>
  );
}
