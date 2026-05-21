import os 
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from generator import generate_surrogate
from loader import load_surrogate_map, load_name_database

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

load_dotenv()

class PiiPayload(BaseModel):
    pii: str = Field(description="Personal Identifiable Information value to be surrogated, e.g. 'John Doe', '01/01/1990', 'New York'")
    entity: str = Field(
        description="Entity tag, e.g. '[[NAME]]', '[[LOCATION]]', '[[DATE]]'",
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    map_path = os.environ.get("SURROGATE_MAP_PATH")
    names_db_path = os.environ.get("NAMES_DB_PATH")
    app.state.surrogate_map_path = map_path
    app.state.name_db = load_name_database(names_db_path)
    app.state.surrogate_map = load_surrogate_map(map_path)
    yield
    app.state.surrogate_map.save(app.state.surrogate_map_path)

app = FastAPI(title="Surrogate Generator", lifespan=lifespan)

@app.post("/pii")
def generate_pii_surrogate(body: PiiPayload, request: Request):
    surrogate = generate_surrogate(
        body.pii,
        body.entity,
        request.app.state.surrogate_map,
        request.app.state.name_db,
    )
    return {
        "pii": body.pii,
        "entity": body.entity,
        "surrogate": surrogate,
    }
