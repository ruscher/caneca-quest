import { expect, test } from "@playwright/test";
import { act, skipTyping } from "./helpers";

// Generates the README screenshots from the real application (run: npx playwright test --project screenshots).
const out = (name: string) => new URL(`../../../docs/screenshots/${name}`, import.meta.url).pathname;

test("capture README screenshots", async ({ page, browser }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await page.waitForTimeout(600);
  await page.screenshot({ path: out("welcome-light.png") });

  await page.getByRole("button", { name: "Nova aventura" }).click();
  await page.getByLabel("Nome da caneca").fill("Aurora");
  await page.getByRole("button", { name: "Avançar" }).click();
  await page.getByText("Terracota", { exact: false }).first().click({ force: true }).catch(() => undefined);
  await page.getByText("Listrada", { exact: true }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: out("create-mug.png") });
  await page.getByRole("button", { name: "Avançar" }).click();
  await page.getByRole("button", { name: "Avançar" }).click();
  await page.getByRole("button", { name: "Despertar" }).click();
  await expect(page.getByRole("log")).toContainText("Você acorda");
  await skipTyping(page);
  for (const cmd of ["conversar com o gato", "perguntar ao gato sobre a voz", "procurar outros objetos vivos"]) {
    await act(page, cmd);
    await skipTyping(page);
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: out("game-light.png") });

  await page.emulateMedia({ colorScheme: "dark" });
  await page.getByRole("tab", { name: "Mapa" }).click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: out("game-dark-map.png") });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, colorScheme: "dark", locale: "pt-BR" });
  await mobile.goto("/");
  await mobile.getByRole("button", { name: /Continuar/ }).click();
  await mobile.waitForTimeout(800);
  await mobile.screenshot({ path: out("mobile-dark.png") });
  await mobile.close();
});
