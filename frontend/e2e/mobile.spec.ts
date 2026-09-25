import { expect, test } from "@playwright/test";
import { ACCOUNTS } from "./helpers";

/** Runs on the Pixel 7 project (see playwright.config.ts). */
test.describe("Mobile", () => {
  test("la navigation mobile ouvre le menu et la recherche reste utilisable", async ({ page }) => {
    await page.goto("/");

    // the desktop nav is hidden; the burger drives navigation
    await page.getByRole("button", { name: "Ouvrir le menu" }).click();
    // The header also has a "Créer un compte" CTA, hidden at this width.
    await expect(
      page.getByRole("navigation").getByRole("link", { name: "Créer un compte" })
    ).toBeVisible();

    // Two search bars exist in the DOM (desktop + mobile); only one is
    // visible at this width, so target the visible one explicitly.
    const search = page.getByPlaceholder(/Que cherchez-vous/).filter({ visible: true }).first();
    await search.fill("tente");
    await search.press("Enter");
    await expect(page).toHaveURL(/search=tente/);
  });

  test("la fiche produit reste lisible sans défilement horizontal", async ({ page }) => {
    await page.goto("/produits");
    await page.locator('a[href^="/produits/"]').first().click();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test("le menu mobile expose favoris et notifications une fois connecté", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Téléphone").fill(ACCOUNTS.visitor.phone);
    await page.getByLabel("Mot de passe").fill(ACCOUNTS.visitor.password);
    await page.getByRole("button", { name: "Se connecter" }).click();
    await expect(page).toHaveURL(/\/compte/);

    await page.getByRole("button", { name: "Ouvrir le menu" }).click();
    // Scope to the burger nav: /compte also renders a "Mes favoris" button.
    const menu = page.getByRole("navigation");
    await expect(menu.getByRole("link", { name: "Mes favoris" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Notifications" })).toBeVisible();
  });
});
