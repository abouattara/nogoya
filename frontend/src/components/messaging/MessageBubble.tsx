"use client";

import clsx from "clsx";
import { Avatar } from "@/components/messaging/Avatar";
import { AttachmentGallery } from "@/components/messaging/AttachmentGallery";
import { SharedProductCard } from "@/components/messaging/SharedProductCard";
import { CheckIcon } from "@/components/messaging/ChatIcons";
import { formatTime } from "@/lib/format";
import type { Message } from "@/lib/types";

/**
 * Une bulle, et ce qui l'entoure.
 *
 * Trois partis pris, tires de ce qui clochait :
 *
 * * **Les suites se collent.** Cinq messages d'affilee portaient cinq
 *   horodatages et cinq pastilles ; seul le dernier d'une serie garde son
 *   heure, et le coin du bas se carre pour marquer la fin du bloc.
 * * **Une note de service n'est pas une bulle.** Le recapitulatif d'une
 *   demande n'est de personne : centre, encadre, titre — jamais aligne du
 *   cote du client, qui croyait l'avoir ecrit.
 * * **Un accuse de lecture, pas une promesse.** Le double trait ne
 *   s'affiche que lorsque `read_at` existe : inventer un « envoye » que le
 *   serveur n'a pas confirme serait mentir sur le seul point ou ce chat
 *   engage NOGOYA.
 */
export function MessageBubble({
  message,
  grouped,
  endsGroup,
}: {
  message: Message;
  /** Suit un message du meme auteur, a quelques minutes pres. */
  grouped: boolean;
  /** Dernier d'une serie : porte l'heure et le coin carre. */
  endsGroup: boolean;
}) {
  if (message.message_type === "system") {
    return (
      <li className="mt-4 flex flex-col items-center">
        <div className="w-full max-w-md rounded-xl border border-brand-200 bg-brand-50 px-3 py-2.5 text-sm text-brand-900">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-brand-700">
            Demande de location
          </p>
          {message.body && <p className="whitespace-pre-line">{message.body}</p>}
          {message.shared_product && <SharedProductCard product={message.shared_product} />}
        </div>
        <span className="mt-1 text-[11px] text-foreground-muted">
          {formatTime(message.created_at)}
        </span>
      </li>
    );
  }

  const mine = message.is_mine;
  const onlyMedia = !message.body && message.attachments.length > 0;

  return (
    <li
      className={clsx(
        "flex items-end gap-2",
        grouped ? "mt-0.5" : "mt-3",
        mine ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* La pastille n'apparait qu'au bas d'une serie ; ailleurs un vide
          de meme largeur garde les bulles alignees. */}
      {mine ? null : endsGroup ? (
        <Avatar name={message.sender.full_name} src={message.sender.avatar} size={28} />
      ) : (
        <span aria-hidden="true" className="w-7 shrink-0" />
      )}

      <div className={clsx("flex min-w-0 max-w-[min(32rem,78%)] flex-col", mine ? "items-end" : "items-start")}>
        <div
          className={clsx(
            "min-w-0 text-sm shadow-sm",
            // Une photo n'a pas besoin d'une marge de texte autour d'elle.
            onlyMedia ? "rounded-2xl p-1" : "rounded-2xl px-3 py-2",
            mine
              ? "bg-brand-600 text-white"
              : "border border-border bg-surface text-foreground",
            endsGroup && (mine ? "rounded-br-md" : "rounded-bl-md")
          )}
        >
          {message.body && <p className="whitespace-pre-line break-words">{message.body}</p>}
          {message.attachments.length > 0 && (
            <div className={message.body ? "mt-2" : undefined}>
              <AttachmentGallery attachments={message.attachments} mine={mine} />
            </div>
          )}
          {message.shared_product && <SharedProductCard product={message.shared_product} />}
        </div>

        {endsGroup && (
          <span className="mt-0.5 flex items-center gap-1 px-1 text-[11px] text-foreground-muted">
            {formatTime(message.created_at)}
            {mine && message.read_at && (
              <>
                <CheckIcon className="h-3 w-3 text-brand-600" />
                <span className="sr-only">Lu</span>
              </>
            )}
          </span>
        )}
      </div>
    </li>
  );
}
