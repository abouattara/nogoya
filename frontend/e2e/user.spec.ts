import { expect, test } from "@playwright/test";
import { ACCOUNTS, jpegFixture, login } from "./helpers";

test.describe("Parcours utilisateur connecté", () => {
  test("favoris : ajouter depuis une annonce, retrouver dans /favoris", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);

    await page.goto("/produits");
    const card = page.locator('a[href^="/produits/"]').first();
    const title = (await card.locator("p").first().textContent())?.trim() ?? "";
    // The SSR markup cannot know this user's favourites; the browser
    // reconciles the hearts right after hydration. Wait for that call, or the
    // first click would act on a stale "not saved" state.
    const favoritesSynced = page.waitForResponse((r) => r.url().includes("/favorites/slugs/"));
    await card.click();
    await expect(page).toHaveURL(/\/produits\/[^/]+$/);
    await favoritesSynced;

    // The detail page's labelled favourite button (cards use icon buttons).
    const favorite = page.getByRole("button", { name: /^(Ajouter aux|Retirer des) favoris$/ }).last();
    await expect(favorite).toBeVisible();

    if ((await favorite.getAttribute("aria-pressed")) === "true") {
      await favorite.click(); // start from a known state
      await expect(favorite).toHaveAttribute("aria-pressed", "false");
    }

    await favorite.click();
    await expect(favorite).toHaveAttribute("aria-pressed", "true");

    await page.goto("/favoris");
    await expect(page.getByRole("heading", { name: "Mes favoris" })).toBeVisible();
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible();
  });

  test("chat : contacter un fournisseur puis envoyer un message", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);

    await page.goto("/produits");
    await page.locator('a[href^="/produits/"]').first().click();
    await page.getByRole("button", { name: /Envoyer un message/ }).click();

    await expect(page).toHaveURL(/\/compte\/messages\/\d+/);

    const message = `Test E2E ${Date.now()}`;
    await page.getByPlaceholder("Écrire un message...").fill(message);
    await page.getByRole("button", { name: "Envoyer" }).click();

    await expect(page.getByText(message)).toBeVisible();

    // it also shows up in the conversation list
    await page.goto("/compte/messages");
    await expect(page.getByText(message)).toBeVisible();
  });

  test("chat : envoyer une photo, la voir dans la conversation", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);
    await page.goto("/compte/messages");
    await page.locator('a[href^="/compte/messages/"]').first().click();
    await expect(page).toHaveURL(/\/compte\/messages\/\d+/);

    // The picker cannot be driven from a test, so the file goes straight
    // into the input — the rest of the path (compression, preview, upload,
    // rendering) is the real one.
    await page.setInputFiles('input[accept="image/*"]', jpegFixture());
    await expect(page.getByRole("img", { name: /Aperçu de/ })).toBeVisible();

    const sent = page.waitForResponse(
      (r) => r.url().includes("/messages/") && r.request().method() === "POST"
    );
    await page.getByRole("button", { name: "Envoyer" }).click();
    const response = await sent;
    expect(response.status()).toBe(201);

    const body = await response.json();
    expect(body.message_type).toBe("image");
    expect(body.attachments).toHaveLength(1);
    // The bubble shows a thumbnail, never the full-size file.
    expect(body.attachments[0].poster_url).toBeTruthy();

    // and the preview list empties once it is sent
    await expect(page.getByRole("img", { name: /Aperçu de/ })).toBeHidden();
  });

  test("chat : un fichier trop lourd est refusé avant l'envoi", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);
    await page.goto("/compte/messages");
    await page.locator('a[href^="/compte/messages/"]').first().click();

    await page.setInputFiles('input[accept="image/*"]', {
      name: "enorme.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.alloc(13 * 1024 * 1024, 1),
    });

    await expect(page.getByRole("alert")).toContainText(/dépasse/);
    await expect(page.getByRole("img", { name: /Aperçu de/ })).toBeHidden();
  });

  test("le bouton micro est disponible dans une conversation", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);
    await page.goto("/compte/messages");

    const conversation = page.locator('a[href^="/compte/messages/"]').first();
    await conversation.click();

    await expect(page.getByRole("button", { name: "Enregistrer un message vocal" })).toBeVisible();
  });

  test("notifications : la cloche et la page listent les notifications", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);

    await page.getByRole("button", { name: /^Notifications/ }).click();
    const seeAll = page.getByRole("link", { name: /Voir toutes les notifications/ });
    await expect(seeAll).toBeVisible();

    await seeAll.click();
    await expect(page).toHaveURL(/\/notifications/);
    await expect(page.getByRole("heading", { name: "Notifications", level: 1 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Non lues", exact: true })).toBeVisible();
  });

  test("le tableau de bord propose des suggestions", async ({ page }) => {
    await login(page, ACCOUNTS.visitor);

    // browse something so the recommendation engine has a signal
    await page.goto("/produits");
    await page.locator('a[href^="/produits/"]').first().click();

    await page.goto("/compte");
    await expect(page.getByRole("heading", { name: "Vus récemment" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Mes informations" })).toBeVisible();
  });
});
