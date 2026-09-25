import { expect, type Page } from "@playwright/test";

/** Django dev server used by the E2E stack (see playwright.config.ts). */
export const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";

/** Accounts created by `python manage.py seed_demo`. */
export const ACCOUNTS = {
  supplier: { phone: "+22670010001", password: "DemoPass123!", name: "Issa" },
  supplier2: { phone: "+22670010002", password: "DemoPass123!", name: "Aminata" },
  visitor: { phone: "+22670020001", password: "DemoPass123!", name: "Fatou" },
};

export async function login(page: Page, account: { phone: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Téléphone").fill(account.phone);
  await page.getByLabel("Mot de passe").fill(account.password);
  await page.getByRole("button", { name: "Se connecter" }).click();
  // The header logout button only exists once the session is bootstrapped,
  // and unlike "Favoris" it appears exactly once on every page.
  await expect(page.getByRole("button", { name: "Déconnexion" })).toBeVisible();
}

export async function logout(page: Page) {
  await page.request.post("/api/auth/logout");
  await page.context().clearCookies();
}

/** A tiny but real JPEG, for upload steps. */
export function jpegFixture() {
  const base64 =
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a" +
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA" +
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==";
  return { name: "photo.jpg", mimeType: "image/jpeg", buffer: Buffer.from(base64, "base64") };
}
