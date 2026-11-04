import { formatDayLabel, sameMessageGroup } from "./format";
import type { Message } from "./types";

/** Un repère de journée, le trait des non-lus, ou un message. */
export type ChatRow =
  | { kind: "day"; key: string; label: string }
  | { kind: "unread"; key: string }
  | { kind: "message"; key: string; message: Message; grouped: boolean; endsGroup: boolean };

const sameDay = (a: Message, b: Message) =>
  new Date(a.created_at).toDateString() === new Date(b.created_at).toDateString();

/**
 * Découpe un fil en journées et en séries de messages.
 *
 * Le calcul vit ici, hors du rendu : une bulle ne peut pas savoir qu'elle
 * termine une série sans regarder la suivante, et lui passer tout le
 * tableau la rendrait dépendante de l'ordre d'affichage. Mis à part, le
 * découpage se teste sans monter d'écran.
 *
 * `firstUnreadId` est l'endroit où la lecture s'était arrêtée, relevé une
 * seule fois par l'écran : il ne bouge plus quand le serveur marque la
 * conversation comme lue, sans quoi le repère s'effacerait au moment où il
 * sert.
 */
export function buildChatRows(messages: Message[], firstUnreadId: number | null): ChatRow[] {
  const rows: ChatRow[] = [];

  messages.forEach((message, index) => {
    const previous = messages[index - 1];
    const next = messages[index + 1];

    const newDay = !previous || !sameDay(previous, message);
    if (newDay) {
      rows.push({ kind: "day", key: `day-${message.id}`, label: formatDayLabel(message.created_at) });
    }
    if (firstUnreadId !== null && message.id === firstUnreadId) {
      rows.push({ kind: "unread", key: `unread-${message.id}` });
    }

    // Une note de service ne se groupe avec rien : elle n'a pas d'auteur.
    const isNote = message.message_type === "system";
    const grouped =
      !newDay &&
      !isNote &&
      message.id !== firstUnreadId &&
      previous?.message_type !== "system" &&
      sameMessageGroup(previous, message);
    const endsGroup =
      isNote ||
      !next ||
      next.message_type === "system" ||
      next.id === firstUnreadId ||
      !sameDay(next, message) ||
      !sameMessageGroup(message, next);

    rows.push({ kind: "message", key: String(message.id), message, grouped, endsGroup });
  });

  return rows;
}
