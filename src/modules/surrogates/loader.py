import pandas as pd
import os
from pathlib import Path
import random
from fuzzywuzzy import fuzz
from dataclasses import dataclass

_MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_NAMES_ROOT = _MODULE_DIR / "config" / "surrogate_db" / "surrogate_names"
DEFAULT_MAP_ROOT = _MODULE_DIR / "config" / "surrogate_map.csv"

@dataclass(frozen=True, slots=True)
class MapEntry:
    word: str
    surrogate: str
    entity: str


class SurrogateMap:
    """In-memory surrogate map. CSV is read at load and written at save only."""

    def __init__(self, map_path) -> None:
        self._map: list[MapEntry] = []
        self._map = self.load_from_csv(map_path)

    def load_from_csv(cls, path: str | None):
        map = cls()
        if path and os.path.exists(path):
            df = pd.read_csv(path)
            for row in df.itertuples(index=False):
                map.add(row.word, row.surrogate, row.entity)
        return map

    def to_dataframe(self) -> pd.DataFrame:
        if not self._map:
            return pd.DataFrame(columns=["word", "surrogate", "entity"])
        return pd.DataFrame(
            [
                {"word": e.word, "surrogate": e.surrogate, "entity": e.entity}
                for e in self._map
            ]
        )

    def save(self, path: str | None) -> None:
        if not path:
            return
        self.to_dataframe().to_csv(path, index=False, encoding="utf-8")

    def add(
        self,
        word: str,
        surrogate: str,
        entity: str
    ) -> None:
        """Append one mapping. Replaces pd.concat + new_entry."""
        self._map.append(
            MapEntry(word=word, surrogate=surrogate, entity=entity)
        )


    def check_exists_in_map(
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
            if fuzz.token_sort_ratio(token_lower, entry.word.lower()) > threshold:
                return True, entry.surrogate
        return False, None


class NameDatabase:
    def __init__(self, names_root):
        self.names_root = names_root
        self._cache = self._build_cache(names_root)

    @staticmethod
    def _read_group_file(path: Path) -> list[str]:
        if not path.is_file():
            return []
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _build_cache(self, names_root: Path) -> dict[tuple[str, str], list[str]]:
        cache: dict[tuple[str, str], list[str]] = {}
        for gender in ("female", "male", "unisex"):
            gender_dir = names_root / gender
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

def load_input(input_file):
    try:
        df = pd.read_csv(input_file)
    except:
        df = pd.DataFrame()
    
    if df.empty:
        print(f"No data found in {input_file}. Exiting.")
        return
    return df

def load_name_database():
    names_root = Path(os.environ.get("SURROGATE_NAMES_DIR", DEFAULT_NAMES_ROOT))
    name_db = NameDatabase(names_root)
    return name_db

def load_surrogate_map(surrogate_map_path):
    surrogate_map_path = surrogate_map_path or os.environ.get("SURROGATE_MAP_PATH", DEFAULT_MAP_ROOT)
    surrogate_map = SurrogateMap(surrogate_map_path)
    return surrogate_map

def save_surrogate_map(surrogate_map, surrogate_map_path):
    surrogate_map.to_csv(surrogate_map_path, index=False, encoding="utf-8")

def save_output(output, output_file):
    output.to_csv(output_file, index=False, encoding="utf-8")