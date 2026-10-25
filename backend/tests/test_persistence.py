"""Database, transactions, concurrency and failure recovery at the service level."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import anyio
import httpx
import pytest
from sqlalchemy import inspect

from caneca.ai.config import AISettings
from caneca.config import Settings
from caneca.game.engine import Engine
from caneca.game.parser import Intent
from caneca.game.state import AdventureSettings, MugIdentity, WorldState
from caneca.persistence.db import Database
from caneca.services.games import CreateGameRequest, GameService, ServiceError, TurnRequest


@pytest.fixture
def service(tmp_path: Path, world) -> Iterator[GameService]:
    db = Database(tmp_path / "t.db")
    db.migrate(tmp_path / "bk")
    yield GameService(db, Engine(world), Settings(data_dir=tmp_path))
    db.dispose()


def new_game(service: GameService) -> str:
    view = service.create_game(
        CreateGameRequest(
            name="T",
            mug=MugIdentity(name="Aurora", color="#f4efe6"),
            settings=AdventureSettings(),
            seed="persist",
        )
    )
    return str(view["id"])


async def collect(service: GameService, game_id: str, text: str) -> list[tuple[str, dict]]:
    return [item async for item in service.play_turn(game_id, TurnRequest(text=text))]


# ---------------------------------------------------------------- schema & backups
def test_migrations_create_schema_from_empty_db(tmp_path: Path):
    db = Database(tmp_path / "empty.db")
    assert db.current_revision() is None
    db.migrate(tmp_path / "bk")
    assert db.current_revision() == db.head_revision()
    tables = set(inspect(db.engine).get_table_names())
    assert {"games", "turns", "journal", "checkpoints", "settings", "alembic_version"} <= tables
    db.migrate(tmp_path / "bk")  # idempotent
    assert not (tmp_path / "bk").exists(), "no backup needed for a fresh database"
    db.dispose()


def test_backup_rotation(tmp_path: Path):
    db = Database(tmp_path / "r.db")
    db.migrate()
    for _ in range(4):
        db.backup(tmp_path / "bk", keep=2)
    files = db.list_backups(tmp_path / "bk")
    assert len(files) == 2
    assert all(f.stat().st_size > 0 for f in files)
    db.dispose()


# ---------------------------------------------------------------- transactions
def test_stale_version_is_rejected(service: GameService):
    gid = new_game(service)
    state, version, _last, _meta = service._load_for_turn(gid)
    outcome = service.engine.resolve(state, Intent(verb="look", raw="olhar"))
    with pytest.raises(ServiceError) as exc:
        service._commit_turn(gid, version + 5, outcome, "olhar", 4)
    assert (exc.value.code, exc.value.status) == ("conflict", 409)
    service._commit_turn(gid, version, outcome, "olhar", 4)
    with pytest.raises(ServiceError):
        service._commit_turn(gid, version, outcome, "olhar", 4)  # same version twice
    assert service.view(gid)["turn"] == 1


def test_concurrent_turn_on_same_game_is_refused(service: GameService):
    gid = new_game(service)

    async def main() -> None:
        first = service.play_turn(gid, TurnRequest(text="olhar"))
        name, _ = await first.__anext__()
        assert name == "outcome"
        second = service.play_turn(gid, TurnRequest(text="olhar"))
        with pytest.raises(ServiceError) as exc:
            await second.__anext__()
        assert (exc.value.code, exc.value.status) == ("turn_in_progress", 409)
        async for _ in first:
            pass
        # Once finished, the game accepts turns again.
        assert [n for n, _ in await collect(service, gid, "olhar")][-1] == "done"

    anyio.run(main)


# ---------------------------------------------------------------- AI failures
class _Stream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[str], fail: bool, delay: float = 0.0) -> None:
        self.chunks, self.fail, self.delay = chunks, fail, delay

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for text in self.chunks:
            if self.delay:
                await anyio.sleep(self.delay)
            yield (json.dumps({"message": {"content": text}, "done": False}) + "\n").encode()
        if self.fail:
            raise httpx.ReadError("connection dropped")
        yield (json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode()


def use_ollama(service: GameService, stream: _Stream) -> None:
    service.transport = httpx.MockTransport(lambda _req: httpx.Response(200, stream=stream))
    service.save_ai_settings(
        AISettings(
            provider="ollama", models={"ollama": "m"}, ai_intent=False, ollama_url="http://ollama.test"
        )
    )


def test_ai_failure_mid_stream_keeps_turn_with_fallback(service: GameService):
    gid = new_game(service)
    use_ollama(service, _Stream(["A chuva ", "cai e "], fail=True))
    events = anyio.run(collect, service, gid, "olhar ao redor")
    names = [n for n, _ in events]
    assert names[0] == "outcome" and "delta" in names
    assert (
        "warning",
        {"code": "ai_unavailable", "detail": "não foi possível conectar ao serviço de IA"},
    ) in events
    done = events[-1][1]
    assert done["source"] == "fallback"
    turn = service.history(gid, None, 10, None)["turns"][-1]
    assert turn["source"] == "fallback" and "mesa" in turn["narration"].lower()
    assert service.view(gid)["turn"] == 1


def test_cancel_marks_turn_and_keeps_state(service: GameService):
    gid = new_game(service)
    use_ollama(service, _Stream([f"palavra{i} " for i in range(40)], fail=False, delay=0.02))

    async def main() -> list[tuple[str, dict]]:
        out = []
        async for name, data in service.play_turn(gid, TurnRequest(text="olhar ao redor")):
            out.append((name, data))
            if name == "delta" and len([n for n, _ in out if n == "delta"]) == 3:
                assert service.cancel(gid)
        return out

    events = anyio.run(main)
    done = events[-1][1]
    assert done["source"] == "cancelled"
    assert done["narration"].startswith("palavra0 palavra1")
    assert "palavra30" not in done["narration"]
    turn = service.history(gid, None, 10, None)["turns"][-1]
    assert turn["source"] == "cancelled"
    assert service.view(gid)["turn"] == 1, "the engine result stays committed"
    assert service.cancel(gid) is False, "nothing left to cancel"


# ---------------------------------------------------------------- import validation
def exported(service: GameService) -> dict:
    gid = new_game(service)
    anyio.run(collect, service, gid, "pegar o torrão")
    return service.export_game(gid)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["turns"][1].update(player_input="x" * 5000),
        lambda d: d.update(format_version=2),
        lambda d: d.update(content_version="2.0.0"),
        lambda d: d.update(format="outro-jogo"),
        lambda d: d["game"].update(name=""),
        lambda d: d["game"]["state"].update(location="lua"),
        lambda d: d["game"]["state"]["npcs"]["noir"].update(relationship=500),
        lambda d: d["game"]["state"].update(abilities=["voar"]),
        lambda d: d["turns"].append(dict(d["turns"][0])),
        lambda d: d["game"].update(extra="campo"),
    ],
)
def test_import_rejects_bad_saves(service: GameService, mutate):
    data = exported(service)
    before = len(service.list_games())
    mutate(data)
    with pytest.raises(ServiceError) as exc:
        service.import_game(json.loads(json.dumps(data)))
    assert exc.value.code == "invalid_save"
    assert len(service.list_games()) == before


def test_import_roundtrip_preserves_state(service: GameService):
    data = exported(service)
    view = service.import_game(data)
    original = WorldState.model_validate(data["game"]["state"])
    assert [i["id"] for i in view["inventory"]] == original.inventory()
    assert len(service.history(view["id"], None, 100, None)["turns"]) == len(data["turns"])
