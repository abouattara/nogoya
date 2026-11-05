import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-border py-8 text-sm text-foreground-muted">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-2 px-4 text-center sm:px-6">
        <p>
          © {new Date().getFullYear()} BINOGOYA — faciliter la location de biens et
          trouver facilement des produits à louer.
        </p>
        {/* Le texte doit rester joignable depuis n'importe quelle page, et
            pas seulement depuis le formulaire d'inscription : on le relit
            surtout quand quelque chose s'est mal passé. */}
        <p>
          <Link href="/conditions" className="underline underline-offset-2 hover:text-foreground">
            Conditions et politique d&apos;utilisation
          </Link>
        </p>
      </div>
    </footer>
  );
}
