"use client";

import { ConversationList } from "@/components/messaging/ConversationList";
import { PendingRequestsBanner } from "@/components/messaging/PendingRequestsBanner";
import { RequireAuth } from "@/components/providers/RequireAuth";

/**
 * L'index de la messagerie.
 *
 * Sur telephone il porte la liste, puisqu'il n'y a pas de colonne. Sur
 * grand ecran la colonne existe deja : repeter la liste au centre
 * reviendrait a l'afficher deux fois, alors on y pose l'invitation a
 * choisir un fil.
 */
export default function MessagesPage() {
  return (
    <RequireAuth>
      {() => (
        <>
          <div className="flex flex-col overflow-y-auto px-4 py-4 sm:px-2 lg:hidden">
            <h1 className="mb-3 px-1 text-2xl font-bold">Messages</h1>
            <PendingRequestsBanner />
            <ConversationList className="overflow-hidden rounded-xl border border-border divide-y divide-border" />
          </div>

          <div className="hidden flex-1 flex-col items-center justify-center gap-2 px-6 text-center lg:flex">
            <p className="text-base font-medium">Choisissez une conversation</p>
            <p className="max-w-sm text-sm text-foreground-muted">
              Chaque échange avec l&apos;équipe NOGOYA tient dans un seul fil : vos
              demandes y arrivent les unes à la suite des autres.
            </p>
          </div>
        </>
      )}
    </RequireAuth>
  );
}
