import { expect, test } from "@playwright/test";
import { ACCOUNTS, API, jpegFixture, login } from "./helpers";

test.describe("Parcours fournisseur", () => {
  test("créer une annonce avec attributs dynamiques et image, puis la modifier", async ({ page }) => {
    await login(page, ACCOUNTS.supplier);

    await page.goto("/compte/fournisseur/produits/nouveau");
    const title = `Berline E2E ${Date.now()}`;

    await page.getByLabel("Titre de l'annonce").fill(title);
    // Options are indented with non-breaking spaces to show the hierarchy,
    // so select by the option element rather than by an exact label string.
    const categorySelect = page.getByLabel("Catégorie");
    const voituresValue = await categorySelect
      .locator("option", { hasText: "Voitures" })
      .first()
      .getAttribute("value");
    await categorySelect.selectOption(voituresValue!);

    // the category's attributes appear once it is chosen
    await expect(page.getByLabel(/^Marque/)).toBeVisible();
    await page.getByLabel(/^Marque/).selectOption("Toyota");
    await page.getByLabel(/^Année/).fill("2020");
    await page.getByLabel("Carburant").selectOption("Diesel");

    await page.getByLabel("Description").fill("Annonce créée par la suite E2E, véhicule en bon état.");
    await page.getByLabel("Type d'offre").selectOption("sale");
    await page.getByLabel("Prix").fill("5500000");
    await page.getByLabel("Ville", { exact: true }).fill("Ouagadougou");

    await page.setInputFiles('input[type="file"]', jpegFixture());
    await expect(page.getByRole("button", { name: /Retoucher/ })).toBeVisible();

    await page.getByRole("button", { name: "Publier l'annonce" }).click();

    await expect(page).toHaveURL(/\/compte\/fournisseur/);
    const row = page.getByRole("row").filter({ hasText: title });
    await expect(row).toBeVisible();
    await expect(row.getByText("En attente de modération")).toBeVisible();

    // edit the published listing — the slug must stay stable
    await row.getByRole("link", { name: "Modifier" }).click();
    await expect(page.getByLabel("Titre de l'annonce")).toHaveValue(title);
    // attributes are pre-filled from what was saved
    await expect(page.getByLabel(/^Marque/)).toHaveValue("Toyota");

    const updated = `${title} (modifiée)`;
    await page.getByLabel("Titre de l'annonce").fill(updated);
    await page.getByRole("button", { name: "Enregistrer les modifications" }).click();

    await expect(page).toHaveURL(/\/compte\/fournisseur/);
    await expect(page.getByRole("row").filter({ hasText: updated })).toBeVisible();
  });

  test("retoucher une image déjà publiée", async ({ page }) => {
    await login(page, ACCOUNTS.supplier);
    await page.goto("/compte/fournisseur");

    await page.getByRole("link", { name: "Modifier" }).first().click();
    await expect(page.getByText("Images actuelles")).toBeVisible();

    const editButton = page.getByRole("button", { name: /^✎ Modifier$/ }).first();
    await editButton.click();

    const editor = page.getByRole("dialog", { name: "Éditeur d'image" });
    await expect(editor).toBeVisible();
    await expect(editor.getByRole("button", { name: "1:1" })).toBeVisible();

    await editor.getByRole("button", { name: /↻ Tourner/ }).click();
    await editor.getByRole("button", { name: "Valider la retouche" }).click();

    // the editor closes once the new render is stored
    await expect(editor).toBeHidden({ timeout: 20_000 });
  });

  test("le tableau de bord affiche les statistiques et les graphiques", async ({ page }) => {
    await login(page, ACCOUNTS.supplier);
    await page.goto("/compte/fournisseur");

    await expect(page.getByText("Produits en ligne")).toBeVisible();
    await expect(page.getByText("Vues totales")).toBeVisible();

    await expect(page.getByRole("heading", { name: "Statistiques" })).toBeVisible();

    const range = page.getByRole("button", { name: "7 jours", exact: true });
    await range.click();
    await expect(range).toHaveAttribute("aria-pressed", "true");

    // either a real chart or the honest "not enough data" state — never a blank box
    await expect
      .poll(async () => {
        const charts = await page.getByRole("img", { name: /Vues/ }).count();
        const empty = await page.getByText("Pas encore assez de données").count();
        return charts + empty;
      })
      .toBeGreaterThan(0);
  });

  test("publier / dépublier une annonce approuvée", async ({ page }) => {
    await login(page, ACCOUNTS.supplier);
    await page.goto("/compte/fournisseur");

    // The table is fetched client-side: counting buttons straight after
    // goto() found none and turned this test into a permanent skip.
    await expect(page.getByRole("heading", { name: "Mes annonces" })).toBeVisible();
    const toggle = page.getByRole("button", { name: /^(Dépublier|Publier)$/ }).first();
    await expect(toggle).toBeVisible();

    const before = await toggle.textContent();
    await toggle.click();
    await expect(page.getByRole("button", { name: /^(Dépublier|Publier)$/ }).first()).not.toHaveText(
      before ?? ""
    );

    // and back, so the suite leaves the listing as it found it
    const restored = page.getByRole("button", { name: /^(Dépublier|Publier)$/ }).first();
    await restored.click();
    await expect(restored).toHaveText(before ?? "");
  });
});

test.describe("Parcours live", () => {
  // The live UI is not built yet (models + API only), so this drives the API
  // directly through Playwright's request context.
  test("créer un live, y associer un produit et l'épingler", async ({ request }) => {
    const auth = await request.post(`${API}/api/v1/auth/login/`, {
      data: { phone: ACCOUNTS.supplier.phone, password: ACCOUNTS.supplier.password },
    });
    expect(auth.ok()).toBeTruthy();
    const { access } = await auth.json();
    const headers = { Authorization: `Bearer ${access}` };

    const liveResponse = await request.post(`${API}/api/v1/lives/`, {
      headers,
      data: { title: `Live E2E ${Date.now()}`, description: "Démo matériel" },
    });
    expect(liveResponse.status()).toBe(201);
    const live = await liveResponse.json();
    expect(live.status).toBe("draft");

    const products = await (
      await request.get(`${API}/api/v1/products/?mine=true`, { headers })
    ).json();
    const productId = products.results[0].id;

    const attach = await request.post(`${API}/api/v1/lives/${live.id}/products/`, {
      headers,
      data: { product: productId },
    });
    expect(attach.ok()).toBeTruthy();

    const pin = await request.post(
      `${API}/api/v1/lives/${live.id}/products/${productId}/pin/`,
      { headers }
    );
    expect((await pin.json()).is_featured).toBe(true);

    // a live starts and ends
    const started = await request.post(`${API}/api/v1/lives/${live.id}/start/`, { headers });
    expect((await started.json()).status).toBe("live");
    const ended = await request.post(`${API}/api/v1/lives/${live.id}/end/`, { headers });
    expect((await ended.json()).status).toBe("ended");
  });
});
