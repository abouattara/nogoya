import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Input, Select, Textarea } from "./Input";
import { Badge, EmptyState, ErrorState } from "./Feedback";
import { Button } from "./Button";

describe("form controls", () => {
  it("associates the label with the input", () => {
    render(<Input id="city" label="Ville" />);
    expect(screen.getByLabelText("Ville")).toBeInTheDocument();
  });

  it("announces validation errors to assistive tech", () => {
    render(<Input id="city" label="Ville" error="Ville requise" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Ville requise");
  });

  it("hides the hint once an error is shown, to avoid noise", () => {
    render(<Input id="city" label="Ville" hint="Ex : Ouagadougou" error="Ville requise" />);

    expect(screen.queryByText("Ex : Ouagadougou")).not.toBeInTheDocument();
  });

  it("gives every field an explicit surface (never transparent)", () => {
    // Guards the historical white-on-white bug: fields must not inherit an
    // unknown ancestor background.
    render(<Input id="city" label="Ville" />);
    expect(screen.getByLabelText("Ville").className).toContain("bg-surface");
  });

  it("renders select options", () => {
    render(
      <Select id="fuel" label="Carburant">
        <option value="diesel">Diesel</option>
      </Select>
    );
    expect(screen.getByRole("option", { name: "Diesel" })).toBeInTheDocument();
  });

  it("renders a textarea", () => {
    render(<Textarea id="desc" label="Description" />);
    expect(screen.getByLabelText("Description").tagName).toBe("TEXTAREA");
  });
});

describe("feedback primitives", () => {
  it("renders a badge with its tone classes", () => {
    render(<Badge tone="brand">Publiée</Badge>);
    expect(screen.getByText("Publiée").className).toContain("text-brand-800");
  });

  it("renders an empty state with its call to action", () => {
    render(
      <EmptyState title="Aucun favori" description="Ajoutez-en un" action={<Button>Voir</Button>} />
    );

    expect(screen.getByText("Aucun favori")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Voir" })).toBeInTheDocument();
  });

  it("offers a retry from the error state", () => {
    render(<ErrorState message="Échec du chargement" retry={() => {}} />);

    expect(screen.getByText("Échec du chargement")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /réessayer/i })).toBeInTheDocument();
  });
});
