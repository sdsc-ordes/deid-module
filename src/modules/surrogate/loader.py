import pandas as pd
import os
from pathlib import Path
import random
from fuzzywuzzy import fuzz
from pydantic import BaseModel, Field

class MapEntry(BaseModel):
    pii: str
    surrogate: str
    entity_type: str = Field(
        description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'",
    )


class SurrogateMap:
    """In-memory surrogate map. CSV is read at load and written at save only."""

    def __init__(self, map_path) -> None:
        self._map: set[MapEntry] = []
        self._load_from_csv(map_path)

    def _load_from_csv(self, path: str | None):
        if path and os.path.exists(path):
            df = pd.read_csv(path)
            for row in df.itertuples(index=False):
                self._map.append(MapEntry(pii=row.pii, surrogate=row.surrogate, entity_type=row.entity_type))

    def _to_dataframe(self) -> pd.DataFrame:
        if not self._map:
            return pd.DataFrame(columns=["pii", "surrogate", "entity_type"])
        return pd.DataFrame(
            [
                {"pii": e.pii, "surrogate": e.surrogate, "entity_type": e.entity_type}
                for e in self._map
            ]
        )

    def save_to_json(self, path: str | None) -> None:
        if not path:
            return
        self._to_dataframe().to_csv(path, index=False, encoding="utf-8")

    def insert(
        self,
        pii: str,
        surrogate: str,
        entity_type: str
    ) -> None:
        """Append one mapping. Replaces pd.concat + new_entry."""
        self._map.append(
            MapEntry(pii=pii, surrogate=surrogate, entity_type=entity_type)
        )


    def find_similar(
        self,
        token: str,
        threshold: int = 80,
    ) -> tuple[bool, str | None]:
        """
        Fuzzy lookup: first entry where token_sort_ratio > threshold.
        """
        if not self._map:
            return False, None

        token_lower = token.lower()
        for entry in self._map:
            if fuzz.token_sort_ratio(token_lower, entry.pii.lower()) > threshold:
                return True, entry.surrogate
        return False, None


class NameDatabase:
    def __init__(self, names_db_path):
        self.names_db_path = Path(names_db_path)
        self._cache = self._build_cache()

    @staticmethod
    def _read_group_file(path: Path) -> list[str]:
        if not path.is_file():
            return []
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _build_cache(self) -> dict[tuple[str, str], list[str]]:
        cache: dict[tuple[str, str], list[str]] = {}
        for gender in ("female", "male", "unisex"):
            gender_dir = self.names_db_path / gender
            if not gender_dir.is_dir():
                continue
            for group_file in sorted(gender_dir.glob("*_group.txt")):
                letter = group_file.stem.removesuffix("_group")  # a_group.txt -> "a"
                names = self._read_group_file(group_file)
                if names:
                    cache[(gender, letter)] = names
        return cache
    
    def pick_random(self, gender: str, first_char: str) -> str:
        names = self._cache.get((gender, first_char.lower()))
        return random.choice(names) if names else "Doe"
