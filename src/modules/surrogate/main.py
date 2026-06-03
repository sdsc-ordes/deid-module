import os
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from contextlib import asynccontextmanager

from generator import generate_surrogate
from loader import NameDatabase, JsonSurrogateMap, SqlSurrogateMap

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

load_dotenv()


class PiiPayload(BaseModel):
    pii: str = Field(description="Personal Identifiable Information value to be surrogated, e.g. 'John Doe', '01/01/1990', 'New York'")
    entity_type: str = Field(
        description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'",
    )


class MapItem(BaseModel):
    pii: str
    entity_type: str
    surrogate: str

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    map_path = Path(_require_env("SURROGATE_MAP_PATH"))
    map_mode = _require_env("SURROGATE_MAP_MODE")
    names_db_path = Path(_require_env("SURROGATE_NAMES_DB_PATH"))
    app.state.names_db = NameDatabase(names_db_path)
    if map_mode == "json":
        app.state.surrogate_map = JsonSurrogateMap(map_path)
    elif map_mode == "sqlite":
        app.state.surrogate_map = SqlSurrogateMap(map_path)
    else:
        raise ValueError(f"Unsupported SURROGATE_MAP_MODE: {map_mode}")
    yield
    if map_mode == "json":
        app.state.surrogate_map.save(map_path)

app = FastAPI(title="Surrogate Generator", lifespan=lifespan)

@app.post("/pii")
def generate_pii_surrogate(body: PiiPayload, request: Request) -> MapItem:
    surrogate = generate_surrogate(
        body.pii,
        body.entity_type,
        request.app.state.surrogate_map,
        request.app.state.names_db,
    )
    return MapItem(pii=body.pii, entity_type=body.entity_type, surrogate=surrogate)


@app.get("/map")
def get_map(request: Request) -> Iterable[MapItem]:
    # data comes from validated map storage
    for entry, surrogate in request.app.state.surrogate_map:
        # model_construct skips validation -> faster instantiation
        yield MapItem.model_construct(
            pii=entry.pii,
            entity_type=entry.entity_type,
            surrogate=surrogate,
        )
