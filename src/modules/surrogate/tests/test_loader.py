import pytest

from loader import JsonSurrogateMap, MapEntry, NameDatabase, SqlSurrogateMap


def entry(pii: str, entity_type: str) -> MapEntry:
    return MapEntry(pii=pii, entity_type=entity_type)


class TestJsonSurrogateMap:
    def test_empty_map_returns_not_found(self, json_map):
        assert json_map.get(entry("anything", "NAME")) is None

    def test_insert_and_lookup(self, json_map):
        json_map.insert(entry("John", "NAME"), "Jane")
        assert json_map.get(entry("John", "NAME")) == "Jane"

    def test_lookup_is_case_insensitive(self, json_map):
        json_map.insert(entry("John", "NAME"), "Jane")
        assert json_map.get(entry("JOHN", "NAME")) == "Jane"
        assert json_map.get(entry("john", "NAME")) == "Jane"

    def test_persist_round_trip(self, tmp_path):
        path = tmp_path / "map.json"
        m = JsonSurrogateMap(path)
        m.insert(entry("1990-01-01", "DATE"), "1993-01-01")
        m.save(path)

        m2 = JsonSurrogateMap(path)
        assert m2.get(entry("1990-01-01", "DATE")) == "1993-01-01"

    def test_reinsert_overwrites(self, json_map):
        json_map.insert(entry("John", "NAME"), "Jane")
        json_map.insert(entry("John", "NAME"), "Janet")
        assert json_map.get(entry("John", "NAME")) == "Janet"


class TestSqlSurrogateMap:
    def test_insert_and_lookup(self, sql_map):
        sql_map.insert(entry("John", "NAME"), "Jane")
        assert sql_map.get(entry("John", "NAME")) == "Jane"

    def test_missing_pii_returns_not_found(self, sql_map):
        assert sql_map.get(entry("nobody", "NAME")) is None

    def test_insert_stores_lowercase(self, sql_map):
        sql_map.insert(entry("JOHN", "NAME"), "Jane")
        assert sql_map.get(entry("john", "NAME")) == "Jane"

    def test_reinsert_overwrites(self, sql_map):
        sql_map.insert(entry("John", "NAME"), "Jane")
        sql_map.insert(entry("John", "NAME"), "Janet")
        assert sql_map.get(entry("John", "NAME")) == "Janet"


class TestNameDatabase:
    @pytest.mark.parametrize("gender,expected", [
        pytest.param("female",        {"Alice", "Anna"},   id="female"),
        pytest.param("male",          {"Aaron", "Adam"},   id="male"),
        pytest.param("mostly_male",   {"Aaron", "Adam"},   id="mostly_male"),
        pytest.param("mostly_female", {"Alice", "Anna"},   id="mostly_female"),
        pytest.param("androgynous",   {"Alex", "Adrian"},  id="androgynous"),
    ])
    def test_pick_random_by_gender(self, names_db, gender, expected):
        assert names_db.pick_random(gender, "a") in expected

    def test_unknown_gender_returns_doe(self, names_db):
        assert names_db.pick_random("unknown", "a") == "Doe"

    def test_none_gender_returns_doe(self, names_db):
        assert names_db.pick_random(None, "a") == "Doe"

    def test_none_first_char_returns_doe(self, names_db):
        assert names_db.pick_random("female", None) == "Doe"

    def test_missing_letter_returns_doe(self, names_db):
        assert names_db.pick_random("female", "z") == "Doe"

    def test_uppercase_first_char_is_normalised(self, names_db):
        assert names_db.pick_random("female", "A") in {"Alice", "Anna"}

    def test_empty_db_returns_doe(self, tmp_path):
        db = NameDatabase(tmp_path)
        assert db.pick_random("female", "a") == "Doe"
