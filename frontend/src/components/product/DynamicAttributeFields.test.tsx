import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DynamicAttributeFields } from "./DynamicAttributeFields";
import { makeAttribute } from "@/test-utils";

describe("DynamicAttributeFields", () => {
  it("renders nothing when the category declares no attribute", () => {
    const { container } = render(
      <DynamicAttributeFields attributes={[]} values={{}} onChange={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a text field and reports what the user types", async () => {
    const onChange = vi.fn();
    render(
      <DynamicAttributeFields
        attributes={[makeAttribute({ name: "Marque", slug: "marque" })]}
        values={{}}
        onChange={onChange}
      />
    );

    await userEvent.type(screen.getByLabelText("Marque"), "T");
    expect(onChange).toHaveBeenCalledWith("marque", "T");
  });

  it("marks required attributes and shows the unit in the label", () => {
    render(
      <DynamicAttributeFields
        attributes={[
          makeAttribute({
            name: "Surface",
            slug: "surface",
            attribute_type: "number",
            unit: "m²",
            required: true,
          }),
        ]}
        values={{}}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Surface (m²) *")).toHaveAttribute("type", "number");
  });

  it("converts number inputs to numbers, not strings", async () => {
    const onChange = vi.fn();
    render(
      <DynamicAttributeFields
        attributes={[makeAttribute({ name: "Année", slug: "annee", attribute_type: "number" })]}
        values={{}}
        onChange={onChange}
      />
    );

    await userEvent.type(screen.getByLabelText("Année"), "9");
    expect(onChange).toHaveBeenCalledWith("annee", 9);
  });

  it("renders declared options for a select attribute", async () => {
    const onChange = vi.fn();
    render(
      <DynamicAttributeFields
        attributes={[
          makeAttribute({
            name: "Carburant",
            slug: "carburant",
            attribute_type: "select",
            options: ["Essence", "Diesel"],
          }),
        ]}
        values={{}}
        onChange={onChange}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText("Carburant"), "Diesel");
    expect(onChange).toHaveBeenCalledWith("carburant", "Diesel");
  });

  it("toggles booleans with a checkbox", async () => {
    const onChange = vi.fn();
    render(
      <DynamicAttributeFields
        attributes={[
          makeAttribute({ name: "Climatisation", slug: "climatisation", attribute_type: "boolean" }),
        ]}
        values={{ climatisation: false }}
        onChange={onChange}
      />
    );

    await userEvent.click(screen.getByLabelText(/climatisation/i));
    expect(onChange).toHaveBeenCalledWith("climatisation", true);
  });

  it("accumulates choices for a multi-select attribute", async () => {
    const onChange = vi.fn();
    render(
      <DynamicAttributeFields
        attributes={[
          makeAttribute({
            name: "Options",
            slug: "options",
            attribute_type: "multi_select",
            options: ["GPS", "Toit ouvrant"],
          }),
        ]}
        values={{ options: ["GPS"] }}
        onChange={onChange}
      />
    );

    await userEvent.click(screen.getByText("Toit ouvrant"));
    expect(onChange).toHaveBeenCalledWith("options", ["GPS", "Toit ouvrant"]);
  });

  it("shows a server-side error next to the field it belongs to", () => {
    render(
      <DynamicAttributeFields
        attributes={[makeAttribute({ name: "Marque", slug: "marque" })]}
        values={{}}
        errors={{ marque: "« Marque » est obligatoire." }}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("obligatoire");
  });
});
