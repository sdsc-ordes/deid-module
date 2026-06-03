import pytest

from loader import JsonSurrogateMap, NameDatabase, SqlSurrogateMap


class TestJsonSurrogateMap:
    def test_empty_map_returns_not_found(self):
        m = JsonSurrogateMap(None)
        assert m.get("anything") == (False, None)

    def test_insert_and_lookup(self, json_map):
        json_map.insert("John", "Jane", "NAME")
        assert json_map.get("John") == (True, "Jane")

    def test_lookup_is_case_insensitive(self, json_map):
        json_map.insert("John", "Jane", "NAME")
        assert json_map.get("JOHN") == (True, "Jane")
        assert json_map.get("john") == (True, "Jane")

    def test_persist_round_trip(self, tmp_path):
        path = tmp_path / "map.json"
        m = JsonSurrogateMap(str(path))
        m.insert("1990-01-01", "1993-01-01", "DATE")
        m.save_to_json()

        m2 = JsonSurrogateMap(str(path))
        assert m2.get("1990-01-01") == (True, "1993-01-01")

    def test_save_with_no_path_is_noop(self):
        m = JsonSurrogateMap(None)
        m.insert("foo", "bar", "LOCATION")
        m.save_to_json()


class TestSqlSurrogateMap:
    def test_insert_and_lookup(self, sql_map):
        sql_map.insert("John", "Jane", "NAME")
        assert sql_map.get("John") == (True, "Jane")

    def test_missing_pii_returns_not_found(self, sql_map):
        assert sql_map.get("nobody") == (False, None)

    def test_insert_stores_lowercase(self, sql_map):
        sql_map.insert("JOHN", "Jane", "NAME")
        assert sql_map.get("john") == (True, "Jane")


class TestNameDatabase:
    @pytest.mark.parametrize("gender,expected", [
        ("female", {"Alice", "Anna"}),
        ("male", {"Aaron", "Adam"}),
        ("mostly_male", {"Aaron", "Adam"}),
        ("mostly_female", {"Alice", "Anna"}),
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
        db = NameDatabase(str(tmp_path))
        assert db.pick_random("female", "a") == "Doe"
