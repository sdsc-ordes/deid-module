import os
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from generator import generate_surrogate
from loader import NameDatabase, JsonSurrogateMap, SqlSurrogateMap, SurrogateMap
from models import Pii, MapItem

load_dotenv()




def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    map_path = Path(_require_env("SURROGATE_MAP_FILE"))
    names_db_path = Path(_require_env("SURROGATE_NAMES_DB_FILE"))
    app.state.names_db = NameDatabase(names_db_path)

    match map_path.suffix:
        case ".json":
            app.state.surrogate_map = JsonSurrogateMap(map_path)
        case ".db" | ".sqlite":
            app.state.surrogate_map = SqlSurrogateMap(map_path)
        case _:
            raise ValueError(f"Unsupported extension: {map_path.suffix}")
    yield
    app.state.surrogate_map.save(map_path)

app = FastAPI(title="Surrogate Generator", lifespan=lifespan)

@app.post("/pii")
def generate_pii_surrogate(body: Pii, request: Request) -> MapItem:
    """Surrogate a single PII value. Idempotent per (pii, entity_type)."""
    surrogate = generate_surrogate(
        body,
        request.app.state.surrogate_map,
        request.app.state.names_db,
    )
    return MapItem(
        pii=body,
        surrogate=surrogate
    )


@app.get("/map")
def export_surrogate_map(request: Request) -> Iterable[MapItem]:
    """Stream all stored mappings as JSON Lines."""
    # data comes from validated map storage
    for item in request.app.state.surrogate_map:
        # model_construct skips validation -> faster instantiation
        yield item


@app.post("/map", status_code=204)
async def import_surrogate_map(request: Request) -> None:
    """Import a stream of MapItems as JSON Lines (one MapItem per line).
    Existing keys are upserted; keys absent from the payload are left unchanged.
    On a malformed line, items inserted before it remain — no rollback."""
    surrogate_map = request.app.state.surrogate_map
    async for line in _iter_lines(request.stream()):
        if line:
            _insert_jsonl(surrogate_map, line)


async def _iter_lines(stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """Yield each newline-delimited line from a byte stream.
    Emit a trailing line without final newline as the last item."""
    buf = bytearray()
    async for chunk in stream:
        buf.extend(chunk)
        while (idx := buf.find(b"\n")) != -1:
            yield bytes(buf[:idx])
            del buf[: idx + 1]
    if buf:
        yield bytes(buf)


def _insert_jsonl(surrogate_map: SurrogateMap, line: bytes) -> None:
    try:
        item = MapItem.model_validate_json(line)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    surrogate_map.insert(item)
