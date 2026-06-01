import os 
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    map_path = os.environ.get("SURROGATE_MAP_PATH")
    map_mode = os.environ.get("SURROGATE_MAP_MODE")
    names_db_path = os.environ.get("SURROGATE_NAMES_DB_PATH")
    app.state.names_db = NameDatabase(names_db_path)
    if map_mode == "json":
        app.state.surrogate_map = JsonSurrogateMap(map_path)
    elif map_mode == "sqlite":
        app.state.surrogate_map = SqlSurrogateMap(map_path)
    else:
        raise ValueError(f"Unsupported SURROGATE_MAP_MODE: {map_mode}")
    yield
    if map_mode == "json":
        app.state.surrogate_map.save_to_json()

app = FastAPI(title="Surrogate Generator", lifespan=lifespan)

@app.post("/pii")
def generate_pii_surrogate(body: PiiPayload, request: Request):
    surrogate = generate_surrogate(
        body.pii,
        body.entity_type,
        request.app.state.surrogate_map,
        request.app.state.names_db,
    )
    return {
        "pii": body.pii,
        "entity_type": body.entity_type,
        "surrogate": surrogate,
    }
