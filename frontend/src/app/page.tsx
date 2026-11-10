import Image from "next/image";
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
      {/* Banniere en bleu profond, pas sur le ruban complet : l'orange
          du logo ne porte que 2,0:1 avec du texte blanc, illisible. Le
          ruban reste donc decoratif, en lisere bas, et le texte repose sur
          le bleu fonce (7,3:1 au plus clair du fond, pour le blanc). */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 to-brand-900 px-6 py-14 text-center">
        {/* La lettre en filigrane, large et debordante. Elle est purement
            decorative — le nom est deja dans le titre de la page et dans
            l'en-tete — donc `aria-hidden` : la repeter n'apprendrait rien
            a un lecteur d'ecran. L'opacite la garde en fond sans jamais
            disputer le contraste du texte. */}
        <Image
          src="/logo-embleme.png"
          alt=""
          width={336}
          height={381}
          aria-hidden="true"
          className="pointer-events-none absolute -right-6 -top-8 h-[125%] w-auto opacity-10 brightness-0 invert select-none"
        />

        <div className="relative flex flex-col items-center gap-6">
          <h1 className="max-w-2xl text-3xl font-bold text-white sm:text-4xl">
            Louez ce dont vous avez besoin, auprès de particuliers et de professionnels
          </h1>
          <p className="max-w-xl text-brand-200">
            Logements, véhicules, équipements, matériel événementiel. Dites-nous ce que vous
            cherchez et pour quelles dates : nous vérifions la disponibilité auprès du
            propriétaire avant de vous mettre en relation.
          </p>
          <SearchBar />
        </div>
        <div className="bg-gradient-brand absolute inset-x-0 bottom-0 h-1.5" aria-hidden="true" />
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
