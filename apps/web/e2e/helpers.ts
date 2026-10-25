import { type Page, expect } from "@playwright/test";

export async function createMug(page: Page, name = "Aurora", opts: { difficulty?: string } = {}) {
  await page.goto("/");
  await page.getByRole("button", { name: "Nova aventura" }).click();
  await page.getByLabel("Nome da caneca").fill(name);
  await page.getByRole("button", { name: "Avançar" }).click();
  await page.getByRole("button", { name: "Avançar" }).click();
  await page.getByRole("button", { name: "Avançar" }).click();
  if (opts.difficulty) await page.getByText(opts.difficulty, { exact: true }).click();
  await page.getByRole("button", { name: "Despertar" }).click();
  await expect(page.getByRole("log", { name: "Narrativa da aventura" })).toContainText("Você acorda");
}

export async function act(page: Page, text: string) {
  const input = page.getByLabel("O que você quer fazer?");
  await expect(input).toBeEnabled();
  await input.fill(text);
  await input.press("Enter");
  await expect(page.getByRole("button", { name: "Agir" })).toBeVisible({ timeout: 15_000 });
}

export async function skipTyping(page: Page) {
  await page.keyboard.press("Escape");
}
