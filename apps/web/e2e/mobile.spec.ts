import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { act, createMug } from "./helpers";

test("mobile: narrative first, panels in sheets, no horizontal scroll", async ({ page }) => {
  await createMug(page, "Nina");
  await act(page, "conversar com o gato");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);

  const composer = page.getByLabel("O que você quer fazer?");
  await expect(composer).toBeInViewport();

  const nav = page.getByRole("navigation", { name: "Painéis da aventura" });
  await nav.getByRole("button", { name: "Missões" }).click();
  await expect(page.getByRole("dialog")).toContainText("O Despertar");
  await page.getByRole("button", { name: "Fechar" }).click();

  await nav.getByRole("button", { name: "Caneca" }).click();
  await expect(page.getByRole("dialog").getByRole("meter", { name: "Temperatura" })).toBeVisible();
  await page.getByRole("button", { name: "Fechar" }).click();

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze();
  expect(results.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
});

test("mobile: touch targets are at least 40px", async ({ page }) => {
  await createMug(page, "Toque");
  const small = await page.evaluate(() =>
    [...document.querySelectorAll("button, a, input, textarea, select")]
      .filter((el) => {
        const r = el.getBoundingClientRect();
        const visuallyHidden = r.width <= 1 || r.height <= 1 || Boolean(el.closest(".sr-only"));
        return !visuallyHidden && (r.height < 40 || r.width < 40);
      })
      .map((el) => `${el.tagName}:${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30)}`),
  );
  expect(small).toEqual([]);
});
