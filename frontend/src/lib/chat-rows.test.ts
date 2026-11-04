import { describe, expect, it } from "vitest";

import { buildChatRows } from "./chat-rows";
import { formatDayLabel, sameMessageGroup } from "./format";
import type { Message, MessageType } from "./types";

function message(
  id: number,
  at: string,
  options: { mine?: boolean; type?: MessageType; read?: boolean } = {}
): Message {
  return {
    id,
    conversation: 1,
    sender: { id: options.mine ? 1 : 2, full_name: "Awa", avatar: null, role: "visitor", created_at: at },
    message_type: options.type ?? "text",
    body: `message ${id}`,
    shared_product: null,
    attachments: [],
    created_at: at,
    read_at: options.read === false ? null : at,
    is_mine: options.mine ?? false,
  };
}

const kinds = (rows: ReturnType<typeof buildChatRows>) => rows.map((r) => r.kind);

describe("buildChatRows", () => {
  it("ouvre chaque journée par son repère", () => {
    const rows = buildChatRows(
      [message(1, "2026-11-01T10:00:00Z"), message(2, "2026-11-02T10:00:00Z")],
      null
    );
    expect(kinds(rows)).toEqual(["day", "message", "day", "message"]);
  });

  it("colle les messages d'une même série et ne garde qu'une heure", () => {
    const rows = buildChatRows(
      [
        message(1, "2026-11-02T10:00:00Z", { mine: true }),
        message(2, "2026-11-02T10:01:00Z", { mine: true }),
        message(3, "2026-11-02T10:02:00Z", { mine: true }),
      ],
      null
    );
    const messages = rows.filter((r) => r.kind === "message");
    expect(messages.map((r) => r.grouped)).toEqual([false, true, true]);
    // Seul le dernier porte l'heure.
    expect(messages.map((r) => r.endsGroup)).toEqual([false, false, true]);
  });

  it("rompt la série quand l'autre répond", () => {
    const rows = buildChatRows(
      [
        message(1, "2026-11-02T10:00:00Z", { mine: true }),
        message(2, "2026-11-02T10:01:00Z", { mine: false }),
      ],
      null
    );
    const messages = rows.filter((r) => r.kind === "message");
    expect(messages.map((r) => r.endsGroup)).toEqual([true, true]);
  });

  it("rompt la série après un long silence", () => {
    const rows = buildChatRows(
      [
        message(1, "2026-11-02T10:00:00Z", { mine: true }),
        message(2, "2026-11-02T10:30:00Z", { mine: true }),
      ],
      null
    );
    const messages = rows.filter((r) => r.kind === "message");
    expect(messages.map((r) => r.grouped)).toEqual([false, false]);
  });

  it("isole une note de service : elle n'a pas d'auteur à qui se coller", () => {
    const rows = buildChatRows(
      [
        message(1, "2026-11-02T10:00:00Z", { mine: false }),
        message(2, "2026-11-02T10:00:30Z", { mine: false, type: "system" }),
        message(3, "2026-11-02T10:01:00Z", { mine: false }),
      ],
      null
    );
    const messages = rows.filter((r) => r.kind === "message");
    expect(messages[1].grouped).toBe(false);
    expect(messages[1].endsGroup).toBe(true);
    // Le message qui suit la note repart seul, pas en suite de la note.
    expect(messages[2].grouped).toBe(false);
  });

  it("pose le trait des nouveaux messages là où la lecture s'était arrêtée", () => {
    const rows = buildChatRows(
      [
        message(1, "2026-11-02T10:00:00Z"),
        message(2, "2026-11-02T10:01:00Z", { read: false }),
        message(3, "2026-11-02T10:02:00Z", { read: false }),
      ],
      2
    );
    expect(kinds(rows)).toEqual(["day", "message", "unread", "message", "message"]);
    // Le message qui ouvre les non-lus ne se colle pas au précédent :
    // le trait passerait entre une bulle et sa suite.
    const messages = rows.filter((r) => r.kind === "message");
    expect(messages[1].grouped).toBe(false);
    expect(messages[0].endsGroup).toBe(true);
  });

  it("ne pose aucun trait quand tout est lu", () => {
    const rows = buildChatRows([message(1, "2026-11-02T10:00:00Z")], null);
    expect(kinds(rows)).not.toContain("unread");
  });

  it("ne rend rien sur un fil vide", () => {
    expect(buildChatRows([], null)).toEqual([]);
  });
});

describe("formatDayLabel", () => {
  const now = new Date("2026-11-04T09:00:00");

  it("nomme aujourd'hui et hier", () => {
    expect(formatDayLabel("2026-11-04T23:30:00", now)).toBe("Aujourd'hui");
    expect(formatDayLabel("2026-11-03T00:05:00", now)).toBe("Hier");
  });

  it("compte en jours civils, pas en heures", () => {
    // 20 minutes d'écart, mais la veille : « Hier », pas « Aujourd'hui ».
    expect(formatDayLabel("2026-11-03T23:50:00", new Date("2026-11-04T00:10:00"))).toBe("Hier");
  });

  it("donne le jour de la semaine dans la semaine écoulée", () => {
    expect(formatDayLabel("2026-11-01T10:00:00", now)).toMatch(/dimanche/i);
  });

  it("ajoute l'année dès qu'on en sort", () => {
    expect(formatDayLabel("2025-06-12T10:00:00", now)).toContain("2025");
    expect(formatDayLabel("2026-01-12T10:00:00", now)).not.toContain("2026");
  });
});

describe("sameMessageGroup", () => {
  it("refuse de grouper sans précédent", () => {
    expect(sameMessageGroup(undefined, { is_mine: true, created_at: "2026-11-02T10:00:00Z" })).toBe(false);
  });

  it("refuse un horodatage qui recule", () => {
    expect(
      sameMessageGroup(
        { is_mine: true, created_at: "2026-11-02T10:05:00Z" },
        { is_mine: true, created_at: "2026-11-02T10:00:00Z" }
      )
    ).toBe(false);
  });
});
