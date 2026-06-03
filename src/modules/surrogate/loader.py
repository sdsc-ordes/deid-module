from __future__ import annotations
import json
import os
import random
import shutil
from pathlib import Path
from typing import Protocol
from collections.abc import Iterator
import sqlite3

from pydantic import BaseModel, Field


class MapEntry(BaseModel, frozen=True):

    pii: str
    entity_type: str = Field(
        description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'",
    )

    def to_sanitized(self) -> MapEntry:
        return MapEntry(
            pii = self.pii.lower(),
            entity_type = self.entity_type,
        )

class SurrogateMap(Protocol):
    """Protocol for a case-insensitive pii → surrogate persistence map."""

    def save(self, map_path: Path) -> None: ...

    def load(self, map_path: Path) -> None: ...

    def insert(self, entry: MapEntry, surrogate: str) -> None: ...

    def get(self, entry: MapEntry) -> str | None: ...

    def __iter__(self) -> Iterator[tuple[MapEntry, str]]: ...



class SqlSurrogateMap:
    """SQLite DB surrogate map."""

    _map_path: Path

    def __init__(self, map_path: Path) -> None:
        self._map_path = map_path

        _ = self._query(
            """
            CREATE TABLE IF NOT EXISTS surrogate_map (
                pii         TEXT NOT NULL,
                surrogate   TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                PRIMARY KEY (pii, entity_type)
            )
            """,
            (),
        )

    def __iter__(self) -> Iterator[tuple[MapEntry, str]]:
        conn = sqlite3.connect(self._map_path)
        try:
            cursor = conn.execute(
                "SELECT pii, surrogate, entity_type FROM surrogate_map"
            )
            for pii, surrogate, entity_type in cursor:
                yield  MapEntry(
                    pii=pii, entity_type=entity_type
                ), surrogate
        finally:
            conn.close()


    def save(self, map_path: Path):
        _ = shutil.copy(self._map_path, map_path)

    def load(self, map_path: Path):
        self._map_path = map_path

    def insert(self, map_entry: MapEntry, surrogate: str) -> None:
        clean_entry = map_entry.to_sanitized()
        _ = self._query(
            "INSERT INTO surrogate_map (pii, entity_type, surrogate) VALUES (?, ?, ?)",
            (clean_entry.pii, clean_entry.entity_type, surrogate),
        )

    def get(self, map_entry: MapEntry) -> str | None:
        clean_entry = map_entry.to_sanitized()
        result = self._query(
            "SELECT surrogate FROM surrogate_map WHERE pii = ?",
            (clean_entry.pii, clean_entry.entity_type),
        ).fetchone()

        return result[0] if result else None

    def _query(self, query: str, values: tuple[str, ...]) -> sqlite3.Cursor:
        with sqlite3.connect(self._map_path) as conn: 
            cursor = conn.cursor()
            return cursor.execute(query,values)
        
    
class JsonSurrogateMap:
    """In-memory surrogate map backed by a set; persisted as JSON.

    The json serialization is:
    [
      [json(MapEntry), surrogate],
    ]

    """

    _map_path: Path

    def __init__(self, map_path: Path) -> None:
        self._map_path = map_path
        # self._map is a private representation optimized for access speed.
        # It is not meant to be serialized as-is.
        self._map: dict[MapEntry, str]
        self.load(map_path)

    def __iter__(self) -> Iterator[tuple[MapEntry, str]]:
        return iter(self._map.items())

    def load(self, map_path: Path) -> None:
        if os.path.exists(map_path):
            with open(map_path, encoding="utf-8") as f:
                self._map = {
                    MapEntry(**entry): surrogate for entry, surrogate in json.load(f)
                }

        raise ValueError("map_path does not exist.")

    def _serialize(self) -> list[tuple[dict[str, str], str]]:
        return [
            (entry.model_dump(), surrogate)
            for entry, surrogate in self._map.items()
        ]

    def save(self, map_path: Path) -> None:
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(self._serialize(), f, indent=2)

    def insert(self, map_entry: MapEntry, surrogate: str) -> None:
        safe_entry = MapEntry(
            pii=map_entry.pii.lower(),
            entity_type=map_entry.entity_type,
        )
        self._map[safe_entry] = surrogate

    def get(
        self,
        map_entry: MapEntry,
    ) -> str | None:
        clean_entry = map_entry.to_sanitized()
        return self._map.get(clean_entry)


_GENDER_LABELS = {
    "male": "male",
    "mostly_male": "male",
    "female": "female",
    "mostly_female": "female",
}


class NameDatabase:
    """Name list indexed by (gender, first_letter), loaded from a directory tree.

    Expected layout::

        <names_db_path>/
            female/   a_group.txt  b_group.txt  …
            male/     a_group.txt  …
            unisex/   a_group.txt  …

    Each file contains one name per line. Missing directories/files are silently skipped;
    pick_random() falls back to "Doe" when no names are found.
    """

    def __init__(self, names_db_path: Path) -> None:
        self.names_db_path = names_db_path
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
        """Return a random name matching gender and starting letter, or 'Doe' as fallback."""
        if gender is None or first_char is None:
            return "Doe"
        if gender=="unknown":
            return "Doe"
        label = self._match_gender(gender)
        names = self._cache.get((label, first_char.lower()))
        print("output from cache:")
        print(names)
        return random.choice(tuple(names)) if names else "Doe"
