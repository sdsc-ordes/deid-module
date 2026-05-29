import json
import os
import random
from pathlib import Path
from typing import Protocol
from abc import abstractmethod
from functools import lru_cache
import sqlite3

from pydantic import BaseModel, ConfigDict, Field


class MapEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    pii: str
    surrogate: str
    entity_type: str = Field(
        description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'",
    )

class SurrogateMap(Protocol):

    @abstractmethod
    def insert(self, pii: str, surrogate: str, entity_type: str):    # Method without a default implementation
        raise NotImplementedError
    
    @abstractmethod
    def exists_in_map(self, pii: str) -> tuple[bool, str | None]:    # Method without a default implementation
        raise NotImplementedError

class SqlSurrogateMap(SurrogateMap):
    """SQLite DB surrogate map."""

    def __init__(self, map_path: str | None) -> None:
        self._map: set[MapEntry] = set()
        self.map_path = map_path
        if self.map_path:
            with sqlite3.connect(self.map_path) as conn: 
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS surrogate_map (
                        pii         TEXT NOT NULL,
                        surrogate   TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        PRIMARY KEY (pii, entity_type)
                    )
                    """
                )
    def insert(self, pii: str, surrogate: str, entity_type: str) -> None:
        with sqlite3.connect(self.map_path) as conn: 
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO surrogate_map (pii, surrogate, entity_type) VALUES (?, ?, ?)",
                (pii.lower(), surrogate, entity_type),
            )

    @lru_cache(10)
    def exists_in_map(self, pii: str) -> tuple[bool, str | None]:
        with sqlite3.connect(self.map_path) as conn: 
            self.cursor = conn.cursor()
            self.cursor.execute(
                "SELECT surrogate FROM surrogate_map WHERE pii = ?",
                (pii.lower(),),
            )
            result = self.cursor.fetchone()
            return (True, result[0]) if result else (False, None)
    
class JsonSurrogateMap (SurrogateMap):
    """In-memory surrogate map backed by a set; persisted as JSON."""

    def __init__(self, map_path: str | None) -> None:
        self._map: set[MapEntry] = set()
        self.map_path = map_path
        self._load_from_json()

    def _load_from_json(self) -> None:
        if self.map_path and os.path.exists(self.map_path):
            with open(self.map_path, encoding="utf-8") as f:
                entries = json.load(f)
            self._map = {MapEntry(**entry) for entry in entries}
        else:
            self._map = set()

    def _to_json(self) -> list[dict]:
        return [entry.model_dump() for entry in self._map]

    def save_to_json(self) -> None:
        if self.map_path:
            with open(self.map_path, "w", encoding="utf-8") as f:
                json.dump(self._to_json(), f, indent=2)

    def insert(self, pii: str, surrogate: str, entity_type: str) -> None:
        self._map.add(MapEntry(pii=pii, surrogate=surrogate, entity_type=entity_type))

    def exists_in_map(
        self,
        pii: str,
    ) -> tuple[bool, str | None]:
        if not self._map:
            return False, None

        pii_lower = pii.lower()
        for entry in self._map:
            if pii_lower == entry.pii.lower():
                return True, entry.surrogate
        return False, None


_GENDER_LABELS = {
    "male": "male",
    "mostly_male": "male",
    "female": "female",
    "mostly_female": "female",
}


class NameDatabase:
    def __init__(self, names_db_path: str | None) -> None:
        self.names_db_path = Path(names_db_path) if names_db_path else Path()
        self._cache: dict[tuple[str, str], set[str]] = self._build_cache()

    @staticmethod
    def _read_group_file(path: Path) -> set[str]:
        if not path.is_file():
            return set()
        return {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def _build_cache(self) -> dict[tuple[str, str], set[str]]:
        cache: dict[tuple[str, str], set[str]] = {}
        for gender in ("female", "male", "unisex"):
            gender_dir = self.names_db_path / gender
            if not gender_dir.is_dir():
                continue
            for group_file in sorted(gender_dir.glob("*_group.txt")):
                letter = group_file.stem.removesuffix("_group")
                names = self._read_group_file(group_file)
                if names:
                    cache[(gender, letter)] = names
        return cache

    @staticmethod
    def _match_gender(predicted: str) -> str:
        return _GENDER_LABELS.get(predicted, "unisex")

    def pick_random(self, gender: str, first_char: str) -> str:
        if gender is None or first_char is None:
            return "Doe"
        if gender=="unknown":
            return "Doe"
        label = self._match_gender(gender)
        names = self._cache.get((label, first_char.lower()))
        print("output from cache:")
        print(names)
        return random.choice(tuple(names)) if names else "Doe"
