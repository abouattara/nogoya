"use client";

import { useSelectedLayoutSegment } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ConversationList } from "@/components/messaging/ConversationList";
import { PendingRequestsBanner } from "@/components/messaging/PendingRequestsBanner";
import { useAuthStore } from "@/store/auth-store";

/**
 * La messagerie en deux panneaux sur grand écran, une page à la fois sur
 * téléphone.
 *
 * Avant, lire un fil puis revenir à la liste demandait deux chargements et
 * faisait perdre sa place — alors qu'une équipe de permanence passe sa
 * journée à sauter d'une conversation à l'autre. La colonne de gauche reste
 * donc montée : changer de fil ne recharge que le panneau de droite.
 *
 * Sous `lg`, la colonne disparaît et c'est la page d'index qui porte la
 * liste : empiler les deux sur un écran de téléphone ne laisserait de
 * place ni à l'une ni à l'autre.
 */
export default function MessagesLayout({ children }: LayoutProps<"/compte/messages">) {
  // `null` sur /compte/messages, l'identifiant du fil sinon.
  const segment = useSelectedLayoutSegment();
  // La colonne interroge l'API : la monter avant de savoir qui lit
  // enverrait une requête vouée au 401. La page, elle, porte déjà son
  // `RequireAuth` et se charge de rediriger.
  const signedIn = useAuthStore((s) => Boolean(s.user));
  const headerHeight = useSiteHeaderHeight();
  useLockedPageScroll();

  return (
    <div className="mx-auto max-w-6xl px-0 sm:px-6">
      <div
        // Mesurée, pas écrite en dur : l'en-tête du site tient sur une
        // rangée en grand et sur deux avec la recherche sur téléphone.
        // Les 4rem supposées plus haut poussaient le champ de saisie sous
        // le bord de l'écran, là où personne ne pouvait écrire.
        style={{ height: `calc(100dvh - ${headerHeight}px)` }}
        className="flex overflow-hidden sm:my-4 sm:rounded-2xl sm:border sm:border-border sm:bg-surface"
      >
        {signedIn && (
          <aside className="hidden w-80 shrink-0 flex-col border-r border-border lg:flex">
            <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
              <h1 className="text-lg font-bold">Messages</h1>
              <Link href="/compte" className="text-xs text-brand-700 underline underline-offset-2">
                Mon compte
              </Link>
            </div>
            <div className="px-3 pt-3">
              <PendingRequestsBanner />
            </div>
            <ConversationList activeId={segment ?? undefined} className="flex-1 overflow-y-auto pb-2" />
          </aside>
        )}

        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}

/**
 * Empêche la page de défiler derrière la messagerie.
 *
 * Le pied de page du site se trouve sous une fenêtre déjà haute d'un
 * écran : au moindre déplacement — la saisie qui s'agrandit, le clavier
 * d'un téléphone — le document glissait et emportait l'en-tête du fil hors
 * de vue, en pleine conversation. Un écran de chat ne défile pas : seule
 * la liste des messages le fait.
 *
 * Le verrou est posé sur `documentElement`, qui porte la barre de
 * défilement, et rendu à l'identique en quittant la messagerie.
 */
function useLockedPageScroll() {
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = previous;
    };
  }, []);
}

/**
 * La hauteur de l'en-tête du site, suivie tant que la messagerie est à
 * l'écran. Avant le premier rendu client on prend 64 px — la valeur d'une
 * rangée : un chat trop court pendant une image se rattrape, un chat trop
 * long cache sa barre d'envoi.
 */
function useSiteHeaderHeight() {
  const [height, setHeight] = useState(64);

  useEffect(() => {
    const header = document.getElementById("site-header");
    if (!header) return;
    const measure = () => setHeight(header.getBoundingClientRect().height);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  return height;
}
