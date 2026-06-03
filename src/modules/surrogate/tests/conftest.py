import pytest
from pathlib import Path

from loader import JsonSurrogateMap, NameDatabase, SqlSurrogateMap

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def names_db_path():
    return FIXTURES_DIR / "names_db"


@pytest.fixture(scope="session")
def names_db(names_db_path):
    return NameDatabase(names_db_path)


@pytest.fixture
def json_map(tmp_path):
    return JsonSurrogateMap(tmp_path / "map.json")


@pytest.fixture
def sql_map(tmp_path):
    return SqlSurrogateMap(tmp_path / "map.db")
