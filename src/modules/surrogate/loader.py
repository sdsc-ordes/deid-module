from __future__ import annotations
import json
import random

from collections.abc import Iterator
import csv
from pathlib import Path
import shutil
from typing import Protocol
from abc import abstractmethod
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
        with sqlite3.connect(self._map_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS surrogate_map (
                    pii         TEXT NOT NULL,
                    surrogate   TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    PRIMARY KEY (pii, entity_type)
                )
                """
            )

    def __iter__(self) -> Iterator[tuple[MapEntry, str]]:
        with sqlite3.connect(self._map_path) as conn:
            rows = conn.execute(
                "SELECT pii, surrogate, entity_type FROM surrogate_map"
            ).fetchall()
        for pii, surrogate, entity_type in rows:
            yield MapEntry(pii=pii, entity_type=entity_type), surrogate

    def save(self, map_path: Path):
        _ = shutil.copy(self._map_path, map_path)

    def load(self, map_path: Path):
        self._map_path = map_path

    def insert(self, map_entry: MapEntry, surrogate: str) -> None:
        clean_entry = map_entry.to_sanitized()
        with sqlite3.connect(self._map_path) as conn:
            conn.execute(
                """
                INSERT INTO surrogate_map (pii, entity_type, surrogate) VALUES (?, ?, ?)
                ON CONFLICT(pii, entity_type) DO UPDATE SET surrogate = excluded.surrogate
                """,
                (clean_entry.pii, clean_entry.entity_type, surrogate),
            )

    def get(self, map_entry: MapEntry) -> str | None:
        clean_entry = map_entry.to_sanitized()
        with sqlite3.connect(self._map_path) as conn:
            row = conn.execute(
                "SELECT surrogate FROM surrogate_map WHERE pii = ? AND entity_type = ?",
                (clean_entry.pii, clean_entry.entity_type),
            ).fetchone()
        return row[0] if row else None



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
        if map_path.exists():
            with open(map_path, encoding="utf-8") as f:
                self._map = {
                    MapEntry(**entry): surrogate for entry, surrogate in json.load(f)
                }
        else:
            self._map = {}

    def _serialize(self) -> list[tuple[dict[str, str], str]]:
        return [
            (entry.model_dump(), surrogate)
            for entry, surrogate in self._map.items()
        ]

    def save(self, map_path: Path) -> None:
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(self._serialize(), f, indent=2)

    def insert(self, map_entry: MapEntry, surrogate: str) -> None:
        self._map[map_entry.to_sanitized()] = surrogate

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
    """Name list indexed by gender, loaded from a CSV file.

    Expected layout::

        <names_db_path>.csv
        name,gender
        Alice,female
        Bob,male

    Missing files are silently skipped;
    pick_random() falls back to "Doe" when no names are found.
    """

    def __init__(self, names_db_path: Path) -> None:
        self.names_db_path = Path(names_db_path)
        self._cache: dict[str, list[str]] = self._build_cache()

    def _build_cache(self) -> dict[str, list[str]]:
        cache: dict[str, list[str]] = {"female": [], "male": [], "unisex": []}
        if not self.names_db_path.is_file():
            return cache

        with self.names_db_path.open(encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                name = row.get("name", "").strip()
                gender = row.get("gender", "").strip().lower()
                if name and gender in cache:
                    cache[gender].append(name)
        return cache

    @staticmethod
    def _match_gender(predicted: str | None) -> str:
        return _GENDER_LABELS.get(predicted, "unisex")


    def pick_random(self, gender: str | None) -> str:
        """Return a random name matching gender, or 'Doe' as fallback."""
        if gender is None:
            return "Doe"
        gender_label = self._match_gender(gender)
        names = self._cache.get(gender_label) or self._cache.get("unisex")
        return random.choice(names) if names else "Doe"
