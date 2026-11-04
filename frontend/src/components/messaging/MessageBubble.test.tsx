import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageBubble } from "./MessageBubble";
import { makeMessage, makeProduct } from "@/test-utils";

function bubbleOf(text: string) {
  // La bulle est le bloc qui porte le fond ; le <p> n'en est que le texte.
  return screen.getByText(text).closest("div")!;
}

describe("MessageBubble", () => {
  it("distingue ses messages de ceux d'en face", () => {
    // Le bug vu par l'équipe : des deux côtés la même couleur, donc une
    // conversation illisible. Les classes exactes peuvent changer ; qu'elles
    // diffèrent, non.
    render(
      <ul>
        <MessageBubble message={makeMessage({ id: 1, body: "À moi", is_mine: true })} grouped={false} endsGroup />
        <MessageBubble message={makeMessage({ id: 2, body: "À l'autre", is_mine: false })} grouped={false} endsGroup />
      </ul>
    );

    expect(bubbleOf("À moi").className).not.toBe(bubbleOf("À l'autre").className);
  });

  it("n'affiche l'heure qu'au bas d'une série", () => {
    const { rerender } = render(
      <ul>
        <MessageBubble message={makeMessage({ body: "Au milieu" })} grouped endsGroup={false} />
      </ul>
    );
    expect(screen.queryByText(/^\d{2}:\d{2}$/)).not.toBeInTheDocument();

    rerender(
      <ul>
        <MessageBubble message={makeMessage({ body: "Au milieu" })} grouped endsGroup />
      </ul>
    );
    expect(screen.getByText(/^\d{2}:\d{2}$/)).toBeInTheDocument();
  });

  it("annonce une note de service pour ce qu'elle est", () => {
    render(
      <ul>
        <MessageBubble
          message={makeMessage({
            message_type: "system",
            body: "Du 4 au 8 novembre",
            shared_product: makeProduct(),
            is_mine: false,
          })}
          grouped={false}
          endsGroup
        />
      </ul>
    );

    expect(screen.getByText("Demande de location")).toBeInTheDocument();
    // Le récapitulatif mène au produit : c'est ce qui manquait au modérateur.
    expect(screen.getByRole("link")).toHaveAttribute("href", "/produits/tente-de-reception");
  });

  it("ne promet « lu » que lorsque le serveur l'a daté", () => {
    const { rerender } = render(
      <ul>
        <MessageBubble message={makeMessage({ body: "Envoyé", is_mine: true, read_at: null })} grouped={false} endsGroup />
      </ul>
    );
    expect(screen.queryByText("Lu")).not.toBeInTheDocument();

    rerender(
      <ul>
        <MessageBubble
          message={makeMessage({ body: "Envoyé", is_mine: true, read_at: "2026-09-20T11:00:00Z" })}
          grouped={false}
          endsGroup
        />
      </ul>
    );
    expect(screen.getByText("Lu")).toBeInTheDocument();
  });
});
