"use client";

import Image from "next/image";
import Link from "next/link";
import { Suspense, useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { SearchBar } from "@/components/search/SearchBar";
import { MessagesLink } from "@/components/layout/MessagesLink";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuthStore } from "@/store/auth-store";
import { useAuth } from "@/components/providers/AuthProvider";

export function Header() {
  const user = useAuthStore((s) => s.user);
  const { logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    // L'identifiant sert a la messagerie, qui mesure cette hauteur pour
    // caler sa fenetre : elle change d'une rangee a deux selon la largeur,
    // et toute valeur ecrite en dur y poussait le champ de saisie hors de
    // l'ecran sur telephone.
    <header
      id="site-header"
      className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur"
    >
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
        {/* La lettre du logo, puis le nom en texte.
            L'image porte l'identite — le degrade du ruban ne se refait pas
            en CSS sans trahir ses courbes — et le nom reste du texte : net
            a toute taille, lu par les moteurs de recherche, et toujours la
            si l'image ne charge pas. Le `alt` est vide parce que le lien
            porte deja son intitule : un lecteur d'ecran annoncerait sinon
            « BINOGOYA BINOGOYA ». */}
        <Link
          href="/"
          aria-label="BINOGOYA, accueil"
          className="flex shrink-0 items-center gap-2"
        >
          <Image
            src="/logo-embleme-96.png"
            alt=""
            width={85}
            height={96}
            priority
            className="h-9 w-auto"
          />
          {/* Deux couleurs, comme sur le logo : « BINOG » en bleu, « OYA »
              en orange. L'orange sur blanc ne tient pas le contraste d'un
              texte courant (2,0:1) ; c'est admis pour un logotype, et le
              nom reste porte par l'`aria-label` du lien. */}
          <span className="hidden text-xl font-extrabold tracking-tight sm:inline" aria-hidden="true">
            <span className="text-brand-500">BINOG</span>
            <span className="text-accent-500">OYA</span>
          </span>
        </Link>

        <div className="hidden flex-1 md:flex">
          <Suspense fallback={<div className="h-9 w-full max-w-xl rounded-full bg-surface-muted" />}>
            <SearchBar compact />
          </Suspense>
        </div>

        <nav className="ml-auto hidden items-center gap-3 md:flex">
          {user?.role === "supplier" && (
            <ButtonLink href="/compte/fournisseur/produits/nouveau" size="sm">
              Publier une annonce
            </ButtonLink>
          )}
          {user ? (
            <div className="flex items-center gap-4">
              <Link href="/favoris" className="text-sm font-medium hover:text-brand-dark">
                Favoris
              </Link>
              <MessagesLink />
              <NotificationBell />
              <Link href="/compte" className="text-sm font-medium hover:text-brand-dark">
                {user.full_name}
              </Link>
              <button onClick={() => logout()} className="text-sm text-foreground-muted hover:text-foreground">
                Déconnexion
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link href="/login" className="text-sm font-medium hover:text-brand-dark">
                Connexion
              </Link>
              <ButtonLink href="/register" size="sm">
                Créer un compte
              </ButtonLink>
            </div>
          )}
        </nav>

        <button
          className="ml-auto flex h-9 w-9 items-center justify-center rounded-lg hover:bg-surface-muted md:hidden"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Ouvrir le menu"
          aria-expanded={menuOpen}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <div className="px-4 pb-3 md:hidden">
        <Suspense fallback={<div className="h-9 w-full rounded-full bg-surface-muted" />}>
          <SearchBar compact />
        </Suspense>
      </div>

      {menuOpen && (
        <nav className="flex flex-col gap-1 border-t border-border px-4 py-3 md:hidden">
          {user ? (
            <>
              {user.role === "supplier" && (
                <Link href="/compte/fournisseur/produits/nouveau" className="rounded-lg px-2 py-2 text-sm font-medium hover:bg-surface-muted">
                  Publier une annonce
                </Link>
              )}
              <MessagesLink compact />
              <Link href="/favoris" className="rounded-lg px-2 py-2 text-sm hover:bg-surface-muted">
                Mes favoris
              </Link>
              <Link href="/notifications" className="rounded-lg px-2 py-2 text-sm hover:bg-surface-muted">
                Notifications
              </Link>
              <Link href="/compte" className="rounded-lg px-2 py-2 text-sm hover:bg-surface-muted">
                Mon compte ({user.full_name})
              </Link>
              <button onClick={() => logout()} className="rounded-lg px-2 py-2 text-left text-sm text-foreground-muted hover:bg-surface-muted">
                Déconnexion
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="rounded-lg px-2 py-2 text-sm hover:bg-surface-muted">
                Connexion
              </Link>
              <Link href="/register" className="rounded-lg px-2 py-2 text-sm font-medium text-brand-dark hover:bg-surface-muted">
                Créer un compte
              </Link>
            </>
          )}
        </nav>
      )}
    </header>
  );
}
