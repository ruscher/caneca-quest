from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caneca.config import Settings
from caneca.game.engine import Engine
from caneca.game.state import AdventureSettings, MugIdentity, WorldState
from caneca.game.world import get_world
from caneca.main import create_app


@pytest.fixture(scope="session")
def world():
    return get_world()


@pytest.fixture
def engine(world) -> Engine:
    return Engine(world)


@pytest.fixture
def new_state(engine):
    def make(seed: str = "test-seed", **settings) -> WorldState:
        return engine.new_state(
            MugIdentity(name="Aurora", color="#f4efe6"),
            AdventureSettings(**settings),
            seed,
        )

    return make


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", rate_limit_per_minute=10_000)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def game(client: TestClient) -> dict:
    resp = client.post(
        "/api/games",
        json={
            "name": "Teste",
            "mug": {"name": "Aurora", "color": "#f4efe6"},
            "settings": {"language": "pt-BR"},
            "seed": "fixed-seed",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def play(client: TestClient, game_id: str, text: str, **extra) -> dict:
    resp = client.post(f"/api/games/{game_id}/turns?stream=false", json={"text": text, **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()
