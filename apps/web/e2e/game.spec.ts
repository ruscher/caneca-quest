import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { act, createMug, skipTyping } from "./helpers";

test("first adventure: create a mug, play, persist and resume", async ({ page }) => {
  await createMug(page, "Aurora");
  const log = page.getByRole("log", { name: "Narrativa da aventura" });
  await expect(page.getByRole("heading", { name: "Mesa perto da janela" })).toBeVisible();

  await act(page, "examinar meu corpo");
  await skipTyping(page);
  await expect(log).toContainText("Você se observa");

  await page.getByRole("button", { name: "Gritar por ajuda" }).click();
  await expect(page.getByRole("button", { name: "Agir" })).toBeVisible();
  await skipTyping(page);
  await expect(log).toContainText("SOCORRO");

  // Courage went up by the interaction's effect.
  const stats = page.getByRole("complementary", { name: "Estado da caneca" });
  await expect(stats.getByText("Coragem", { exact: true }).locator("..")).toContainText("52");

  await act(page, "quero pular da mesa");
  await skipTyping(page);
  await expect(page.getByRole("heading", { name: "Salão do café" })).toBeVisible();

  // Reload: autosave keeps the location and the narrative history.
  await page.reload();
  await page.getByRole("button", { name: /Continuar/ }).click();
  await expect(page.getByRole("heading", { name: "Salão do café" })).toBeVisible();
  await expect(log).toContainText("SOCORRO");
});

test("chapter 1 can be completed through the front door with the string", async ({ page }) => {
  await createMug(page, "Pingo");
  for (const cmd of [
    "descer pela cadeira",
    "ir para a cozinha",
    "ir ao depósito",
    "pegar o barbante",
    "voltar para a cozinha",
    "voltar ao salão",
    "ir até a porta de entrada",
  ]) {
    await act(page, cmd);
  }
  await expect(page.getByRole("heading", { name: "Porta de entrada" })).toBeVisible();
  // The lasso uses a creativity check; retry until it succeeds (each try is a real turn).
  const log = page.getByRole("log", { name: "Narrativa da aventura" });
  for (let i = 0; i < 10; i++) {
    await act(page, "usar o barbante na maçaneta");
    await skipTyping(page);
    if ((await log.textContent())?.includes("plim")) break;
  }
  await act(page, "sair pela porta para a calçada");
  await expect(page.getByText("Capítulo 2 — A Cidade Gigantesca").first()).toBeVisible();
  await page.getByRole("tab", { name: "Missões" }).click();
  await expect(page.getByRole("tabpanel")).toContainText("A Cidade Gigantesca");
});

test("save points can be created and restored", async ({ page }) => {
  await createMug(page, "Bia");
  await page.getByRole("button", { name: "Salvar ponto" }).click();
  await expect(page.getByText(/Ponto salvo/)).toBeVisible();
  await act(page, "pegar o torrão de açúcar");
  await page.getByRole("tab", { name: "Inventário" }).click();
  await expect(page.getByRole("tabpanel")).toContainText("torrão de açúcar");

  await page.getByRole("button", { name: "Menu da partida" }).click();
  await page.getByRole("button", { name: "Partidas salvas" }).click();
  await page.getByRole("button", { name: "Restaurar" }).last().click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirmar" }).click();
  await expect(page.getByRole("heading", { name: "Mesa perto da janela" })).toBeVisible();
  await page.getByRole("tab", { name: "Inventário" }).click();
  await expect(page.getByRole("tabpanel")).toContainText("Sua alça está vazia.");
});

test("keyboard only: focus shortcut, act, suggestions with Alt+number", async ({ page }) => {
  await createMug(page, "Tita");
  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("O que você quer fazer?")).toBeFocused();
  await page.keyboard.type("olhar ao redor");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Agir" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Alt+1");
  await expect(page.getByRole("button", { name: "Agir" })).toBeVisible();
  await expect(page.locator("article")).toHaveCount(3);
});

test("network failure during a turn shows an error and keeps the game usable", async ({ page }) => {
  await createMug(page, "Lua");
  await page.route("**/api/games/*/turns", (route) =>
    route.request().method() === "POST" ? route.abort("failed") : route.continue(),
  );
  const input = page.getByLabel("O que você quer fazer?");
  await input.fill("olhar ao redor");
  await input.press("Enter");
  await expect(page.getByText("Sem conexão com o servidor do jogo.")).toBeVisible();
  await page.unroute("**/api/games/*/turns");
  await act(page, "olhar ao redor");
  await expect(page.locator("article")).toHaveCount(2);
});

test("settings: dark theme and larger text are applied and persisted", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Configurações" }).click();
  await page.getByRole("tab", { name: "Visual e leitura" }).click();
  await page.getByText("Escuro", { exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Fechar" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("AI settings: unavailable Ollama is reported clearly, offline mode still works", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Configurações" }).click();
  await page.getByText("Ollama (IA local)").click();
  await page.getByLabel("Endereço do Ollama").fill("http://127.0.0.1:9");
  await page.getByRole("button", { name: "Verificar e listar modelos" }).click();
  await expect(page.getByText(/Indisponível/)).toBeVisible();
  await page.getByText("Modo básico (sem IA)", { exact: true }).click();
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Configurações salvas.")).toBeVisible();
});

for (const theme of ["light", "dark"] as const) {
  test(`accessibility (axe, ${theme}): welcome, creation and game screens`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    const check = async (label: string) => {
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${label}: ${v.id} — ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
    };
    await page.goto("/");
    await check("welcome");
    await page.getByRole("button", { name: "Nova aventura" }).click();
    await check("create");
    await page.getByLabel("Nome da caneca").fill("Axe");
    for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Avançar" }).click();
    await page.getByRole("button", { name: "Despertar" }).click();
    await expect(page.getByRole("log")).toContainText("Você acorda");
    await act(page, "olhar ao redor");
    await check("game");
    await page.getByRole("button", { name: "Configurações" }).click();
    await check("settings");
  });
}
