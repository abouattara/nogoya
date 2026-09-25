import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LineChart } from "./LineChart";
import { BarList } from "./BarList";
import { makeSeries } from "@/test-utils";

describe("LineChart", () => {
  it("says so rather than drawing an empty chart when there is no data", () => {
    render(<LineChart data={makeSeries([0, 0, 0])} label="Vues" />);

    expect(screen.getByText("Pas encore assez de données")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("handles a completely empty series", () => {
    render(<LineChart data={[]} label="Vues" />);

    expect(screen.getByText("Pas encore assez de données")).toBeInTheDocument();
  });

  it("plots the series and totals it for screen readers", () => {
    render(<LineChart data={makeSeries([1, 4, 2])} label="Vues" />);

    expect(screen.getByRole("img", { name: /vues : 7 au total/i })).toBeInTheDocument();
    expect(screen.getByText("7 au total")).toBeInTheDocument();
  });
});

describe("BarList", () => {
  it("falls back to the empty state when every value is zero", () => {
    render(<BarList title="Top annonces" items={[{ label: "Tente", value: 0 }]} />);

    expect(screen.getByText("Pas encore assez de données")).toBeInTheDocument();
  });

  it("lists items with their values and links", () => {
    render(
      <BarList
        title="Top annonces"
        unit="vues"
        items={[
          { label: "Tente", value: 12, href: "/produits/tente" },
          { label: "Berline", value: 4 },
        ]}
      />
    );

    expect(screen.getByRole("link", { name: "Tente" })).toHaveAttribute("href", "/produits/tente");
    expect(screen.getByText("12 vues")).toBeInTheDocument();
    expect(screen.getByText("4 vues")).toBeInTheDocument();
  });
});
