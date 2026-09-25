import { expect, test } from "@playwright/test";

test.describe("Parcours visiteur", () => {
  test("accueil → recherche → filtre → produit → fournisseur", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Louez ou achetez");

    // search from the hero
    await page.getByPlaceholder(/Que cherchez-vous/).first().fill("tente");
    await page.getByRole("button", { name: "Rechercher" }).first().click();
    await expect(page).toHaveURL(/\/produits\?.*search=tente/);
    await expect(page.getByText(/résultat/)).toBeVisible();

    // narrow with the listing-type filter
    await page.getByRole("link", { name: "Location", exact: true }).click();
    await expect(page).toHaveURL(/listing_type=rent/);

    // open the first result
    const firstCard = page.locator('a[href^="/produits/"]').first();
    const title = (await firstCard.locator("p").first().textContent())?.trim();
    await firstCard.click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(title ?? "");

    // localisation block with the Google Maps deep link
    await expect(page.getByRole("heading", { name: "Localisation" })).toBeVisible();
    const mapLink = page.getByRole("link", { name: /Voir sur Google Maps/ });
    await expect(mapLink).toHaveAttribute("href", /google\.com\/maps/);

    // anonymous visitors are invited to sign in rather than shown the phone
    await expect(page.getByRole("link", { name: "Connectez-vous" })).toBeVisible();

    // jump to the supplier catalogue
    await page.getByRole("link", { name: /^Issa|^Aminata/ }).first().click();
    await expect(page).toHaveURL(/\/fournisseurs\//);
    await expect(page.getByRole("heading", { name: "Catalogue" })).toBeVisible();
    await expect(page.getByLabel("Rechercher dans ce catalogue")).toBeVisible();
  });

  test("les filtres par caractéristique apparaissent pour une catégorie qui en déclare", async ({ page }) => {
    await page.goto("/produits?category=voitures");

    await expect(page.getByRole("heading", { name: "Caractéristiques" })).toBeVisible();
    const fuel = page.getByLabel("Carburant");
    await expect(fuel).toBeVisible();

    await fuel.selectOption("Diesel");
    await expect(page).toHaveURL(/attr_carburant=Diesel/);
    await expect(page.getByText(/résultat/)).toBeVisible();
  });

  test("un état vide utile plutôt qu'une page blanche", async ({ page }) => {
    await page.goto("/produits?search=zzzzintrouvablezzzz");

    await expect(page.getByText("Aucun article trouvé")).toBeVisible();
    await expect(page.getByText(/élargir votre recherche/)).toBeVisible();
  });

  test("favoriter demande de se connecter", async ({ page }) => {
    await page.goto("/produits");
    await page.getByRole("button", { name: "Ajouter aux favoris" }).first().click();

    await expect(page).toHaveURL(/\/login/);
  });

  test("l'identifiant visiteur reste le même d'une page à l'autre", async ({ page, context }) => {
    // It used to be re-minted on every render, which silently broke view
    // de-duplication and the "recently viewed" history.
    await page.goto("/");
    const read = async () =>
      (await context.cookies()).find((c) => c.name === "nogoya_vid")?.value;

    const first = await read();
    expect(first).toMatch(/^[0-9a-f]{32}$/);

    await page.goto("/produits");
    await page.locator('a[href^="/produits/"]').first().click();
    expect(await read()).toBe(first);
  });
});
