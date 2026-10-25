"""Performance measurements for the backend (offline mode, no AI).

Usage: uv run python scripts/bench.py [--turns 2000] [--json out.json]
Prints measured numbers; nothing here is estimated except prompt tokens (chars / 4).
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import anyio
from fastapi.testclient import TestClient

from caneca.ai.prompts import build_narration_prompt
from caneca.config import Settings
from caneca.game.engine import Engine
from caneca.game.i18n import lt
from caneca.game.state import AdventureSettings, Fact, MugIdentity
from caneca.game.world import get_world
from caneca.main import create_app
from caneca.memory.context import RecentTurn, budget_for, select_memory
from caneca.services.games import GameService, TurnRequest

# A loop of free-text commands that walks around the café without ending the game.
SCRIPT = [
    "olhar ao redor",
    "examinar o quadro",
    "ir para o balcão",
    "falar com dona doce",
    "perguntar sobre os torrões",
    "examinar a caixa registradora",
    "descer para o salão",
    "esperar",
    "ir para a cozinha",
    "falar com o moedor",
    "examinar o fogão",
    "voltar ao salão",
    "gritar",
    "descansar",
    "examinar meu corpo",
]


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1))))
    return ordered[k]


def summary(ms: list[float]) -> dict[str, float]:
    return {
        "n": len(ms),
        "p50_ms": round(pct(ms, 50), 3),
        "p95_ms": round(pct(ms, 95), 3),
        "max_ms": round(max(ms), 3),
        "mean_ms": round(statistics.fmean(ms), 3),
    }


def timed(fn: Callable[[], Any]) -> tuple[float, Any]:
    t0 = time.perf_counter()
    result = fn()
    return (time.perf_counter() - t0) * 1000, result


def rss_mb() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return float("nan")


def keep_alive(state: Any) -> None:
    state.stats.energy = 100.0
    state.stats.temperature = 80.0
    state.stats.integrity = 95.0


def bench_engine(turns: int) -> dict[str, Any]:
    engine = Engine(get_world())
    state = engine.new_state(MugIdentity(name="Bench", color="#f4efe6"), AdventureSettings(), "bench")
    state.location = "salao"
    parse_ms, resolve_ms = [], []
    last = None
    for i in range(turns):
        text = SCRIPT[i % len(SCRIPT)]
        dt, intent = timed(lambda t=text, s=state, ln=last: engine.interpret(s, t, ln))
        parse_ms.append(dt)
        dt, out = timed(lambda s=state, it=intent: engine.resolve(s, it))
        resolve_ms.append(dt)
        state = out.state
        last = out.dialogue_npc or last
        keep_alive(state)
    return {
        "interpret": summary(parse_ms),
        "resolve": summary(resolve_ms),
        "final_turn": state.turn,
        "facts": len(state.facts),
    }


def bench_api(data_dir: Path, turns: int, api_turns: int) -> dict[str, Any]:
    settings = Settings(data_dir=data_dir, rate_limit_per_minute=10_000_000)
    t0 = time.perf_counter()
    with TestClient(create_app(settings)) as client:
        startup_ms = (time.perf_counter() - t0) * 1000
        service: GameService = client.app.state.games  # type: ignore[attr-defined]
        game = client.post(
            "/api/games",
            json={
                "name": "Bench",
                "mug": {"name": "Bench", "color": "#f4efe6"},
                "seed": "bench",
            },
        ).json()
        gid = game["id"]

        api_ms = []
        for i in range(api_turns):
            text = SCRIPT[i % len(SCRIPT)]
            dt, resp = timed(
                lambda t=text: client.post(f"/api/games/{gid}/turns?stream=false", json={"text": t})
            )
            assert resp.status_code == 200, resp.text
            api_ms.append(dt)

        # Grow a long adventure through the service (same code path, minus HTTP).
        async def grow(n: int) -> None:
            for i in range(n):
                async for _ in service.play_turn(gid, TurnRequest(text=SCRIPT[i % len(SCRIPT)])):
                    pass
                if i % 50 == 0:  # keep the mug alive for the benchmark
                    with service.db.session() as s:
                        from caneca.persistence.orm import GameRow

                        row = s.get(GameRow, gid)
                        assert row is not None
                        st = dict(row.state)
                        st["stats"] = {**st["stats"], "energy": 100.0, "temperature": 80.0, "integrity": 95.0}
                        row.state = st

        t0 = time.perf_counter()
        anyio.run(grow, turns - api_turns)
        grow_s = time.perf_counter() - t0

        view_ms = [timed(lambda: client.get(f"/api/games/{gid}"))[0] for _ in range(50)]
        hist_ms = [timed(lambda: client.get(f"/api/games/{gid}/turns?limit=40"))[0] for _ in range(50)]
        old_ms = [
            timed(lambda: client.get(f"/api/games/{gid}/turns?limit=40&before=200"))[0] for _ in range(50)
        ]
        journal_ms = [timed(lambda: client.get(f"/api/games/{gid}/journal"))[0] for _ in range(20)]
        list_ms = [timed(lambda: client.get("/api/games"))[0] for _ in range(20)]
        export_ms, exported = timed(lambda: client.get(f"/api/games/{gid}/export"))
        total_turns = client.get(f"/api/games/{gid}").json()["turn"]

        # Prompt size the narrator would receive at the end of this long game.
        state, _v, last_npc, _m = service._load_for_turn(gid)
        engine = service.engine
        out = engine.resolve(state, engine.interpret(state, "olhar ao redor", last_npc))
        recent = [RecentTurn(i, SCRIPT[i % len(SCRIPT)], "narração " * 60) for i in range(4)]
        # Stress the memory selector: a long adventure with 300 recorded facts.
        stressed = out.state.model_copy(deep=True)
        for i in range(300):
            stressed.facts[f"bench{i}"] = Fact(
                id=f"bench{i}",
                text=lt(f"Fato {i}: " + "detalhe " * 15, f"Fact {i}"),
                turn=i,
                importance=1 + i % 5,
                location="salao",
                tags=["dona_doce"] if i % 7 == 0 else [],
            )
        prompt_sizes = {}
        for ctx in (2048, 4096, 8192):
            mem = select_memory(
                stressed,
                "pt-BR",
                {out.state.location},
                "olhar ao redor",
                recent,
                "resumo " * 400,
                budget_for(ctx, 280),
            )
            p = build_narration_prompt(engine, stressed, out, mem, [])
            chars = len(p.system) + len(p.user)
            prompt_sizes[str(ctx)] = {
                "chars": chars,
                "est_tokens": chars // 4,
                "facts_included": len(mem.facts),
                "facts_dropped": mem.dropped_facts,
            }

    db_bytes = settings.db_path.stat().st_size + sum(
        p.stat().st_size for p in data_dir.glob("caneca.db-*") if p.is_file()
    )
    return {
        "startup_ms": round(startup_ms, 1),
        "api_turn_offline": summary(api_ms),
        "grow_turns_per_s": round((turns - api_turns) / grow_s, 1),
        "game_turns": total_turns,
        "get_game_view": summary(view_ms),
        "history_latest_page": summary(hist_ms),
        "history_older_page": summary(old_ms),
        "journal": summary(journal_ms),
        "list_games": summary(list_ms),
        "export_ms": round(export_ms, 1),
        "export_bytes": len(exported.content),
        "db_bytes": db_bytes,
        "prompt": prompt_sizes,
    }


def machine() -> dict[str, Any]:
    cpu = "?"
    cores = 0
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name") and cpu == "?":
                cpu = line.split(":", 1)[1].strip()
            if line.startswith("processor"):
                cores += 1
    except OSError:
        pass
    mem = "?"
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                mem = f"{int(line.split()[1]) / 1024 / 1024:.1f} GiB"
    except OSError:
        pass
    return {
        "cpu": cpu,
        "logical_cpus": cores,
        "memory": mem,
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=2000)
    parser.add_argument("--api-turns", type=int, default=200)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    results: dict[str, Any] = {"machine": machine()}
    results["engine"] = bench_engine(args.turns)
    with tempfile.TemporaryDirectory() as tmp:
        results["api"] = bench_api(Path(tmp), args.turns, args.api_turns)
    results["rss_mb"] = round(rss_mb(), 1)
    text = json.dumps(results, indent=2, ensure_ascii=False)
    print(text)
    if args.json:
        args.json.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
