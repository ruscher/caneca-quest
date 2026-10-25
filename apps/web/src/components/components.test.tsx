import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useGame } from "../store/game";
import { usePrefs } from "../store/prefs";
import { gameView } from "../test/fixtures";
import { Composer } from "./game/Composer";
import { MugAvatar } from "./game/MugAvatar";
import { Meter, Tabs, Toggle } from "./ui/primitives";

beforeEach(() => {
  usePrefs.setState({ language: "pt-BR" });
  useGame.setState({ game: gameView(), phase: "idle", commandHistory: ["olhar ao redor"], feed: [] });
});

describe("Composer", () => {
  it("submits with Enter and clears the field", async () => {
    const act = vi.fn().mockResolvedValue(undefined);
    useGame.setState({ act });
    render(<Composer />);
    const input = screen.getByLabelText("O que você quer fazer?");
    await userEvent.type(input, "pegar o torrão{Enter}");
    expect(act).toHaveBeenCalledWith("pegar o torrão", null);
    expect(input).toHaveValue("");
  });

  it("disables sending an empty action", () => {
    render(<Composer />);
    expect(screen.getByRole("button", { name: "Agir" })).toBeDisabled();
  });

  it("recalls previous actions with the up arrow", async () => {
    render(<Composer />);
    const input = screen.getByLabelText("O que você quer fazer?");
    await userEvent.click(input);
    await userEvent.keyboard("{ArrowUp}");
    expect(input).toHaveValue("olhar ao redor");
  });

  it("sends suggestions with their structured intent", async () => {
    const act = vi.fn().mockResolvedValue(undefined);
    useGame.setState({ act });
    render(<Composer />);
    await userEvent.click(screen.getByRole("button", { name: /Gritar por ajuda/ }));
    expect(act).toHaveBeenCalledWith("Gritar por ajuda", expect.objectContaining({ interaction: "mesa_gritar" }));
  });

  it("offers cancel while a turn is running", async () => {
    const cancel = vi.fn();
    useGame.setState({ phase: "narrating", cancel });
    render(<Composer />);
    await userEvent.click(screen.getByRole("button", { name: "Interromper" }));
    expect(cancel).toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("O narrador está escrevendo…");
  });
});

describe("primitives", () => {
  function TabsHarness() {
    const [active, setActive] = useState("a");
    return (
      <Tabs
        label="Painéis"
        active={active}
        onChange={setActive}
        tabs={[
          { id: "a", label: "Primeira" },
          { id: "b", label: "Segunda" },
          { id: "c", label: "Terceira" },
        ]}
      />
    );
  }

  it("tabs follow the WAI-ARIA keyboard pattern", async () => {
    render(<TabsHarness />);
    const first = screen.getByRole("tab", { name: "Primeira" });
    first.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Segunda" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Segunda" })).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Terceira" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Primeira" })).toHaveAttribute("aria-selected", "true");
  });

  it("meters expose value and text, not only color", () => {
    render(<Meter label="Café" value={74.6} icon="cup" tone="text-coffee" hint="flutuante" />);
    const meter = screen.getByRole("meter", { name: "Café" });
    expect(meter).toHaveAttribute("aria-valuenow", "75");
    expect(meter).toHaveAttribute("aria-valuetext", "75% — flutuante");
    expect(meter).toHaveTextContent("75%");
  });

  it("toggle is a switch", async () => {
    const onChange = vi.fn();
    render(<Toggle label="Som" checked={false} onChange={onChange} />);
    await userEvent.click(screen.getByRole("switch", { name: "Som" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("mug portrait is labelled and shows cracks when damaged", () => {
    const { container } = render(
      <MugAvatar mug={{ color: "#2f5d8a", style: "striped", drink: "tea" }} label="Retrato" state={{ integrity: 15 }} animated={false} />,
    );
    expect(screen.getByRole("img", { name: "Retrato" })).toBeInTheDocument();
    expect(container.querySelectorAll('path[d^="M70 40"], path[d^="M34 52"]').length).toBe(2);
  });
});
