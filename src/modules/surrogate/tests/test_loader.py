import pytest

from loader import JsonSurrogateMap, NameDatabase, SqlSurrogateMap


class TestJsonSurrogateMap:
    def test_empty_map_returns_not_found(self):
        m = JsonSurrogateMap(None)
        assert m.exists_in_map("anything") == (False, None)

    def test_insert_and_lookup(self, json_map):
        json_map.insert("John", "Jane", "NAME")
        assert json_map.exists_in_map("John") == (True, "Jane")

    def test_lookup_is_case_insensitive(self, json_map):
        json_map.insert("John", "Jane", "NAME")
        assert json_map.exists_in_map("JOHN") == (True, "Jane")
        assert json_map.exists_in_map("john") == (True, "Jane")

    def test_persist_round_trip(self, tmp_path):
        path = tmp_path / "map.json"
        m = JsonSurrogateMap(str(path))
        m.insert("1990-01-01", "1993-01-01", "DATE")
        m.save_to_json()

        m2 = JsonSurrogateMap(str(path))
        assert m2.exists_in_map("1990-01-01") == (True, "1993-01-01")

    def test_save_with_no_path_is_noop(self):
        m = JsonSurrogateMap(None)
        m.insert("foo", "bar", "LOCATION")
        m.save_to_json()  # must not raise


class TestSqlSurrogateMap:
    def test_insert_and_lookup(self, sql_map):
        sql_map.insert("John", "Jane", "NAME")
        assert sql_map.exists_in_map("John") == (True, "Jane")

    def test_missing_pii_returns_not_found(self, sql_map):
        assert sql_map.exists_in_map("nobody") == (False, None)

    def test_insert_stores_lowercase(self, sql_map):
        # insert() lowercases pii before storing; exists_in_map() also lowercases the query
        sql_map.insert("JOHN", "Jane", "NAME")
        assert sql_map.exists_in_map("john") == (True, "Jane")


class TestNameDatabase:
    def test_pick_random_female(self, names_db):
        assert names_db.pick_random("female", "a") in {"Alice", "Anna"}

    def test_pick_random_male(self, names_db):
        assert names_db.pick_random("male", "a") in {"Aaron", "Adam"}

    def test_mostly_male_maps_to_male(self, names_db):
        assert names_db.pick_random("mostly_male", "a") in {"Aaron", "Adam"}

    def test_mostly_female_maps_to_female(self, names_db):
        assert names_db.pick_random("mostly_female", "a") in {"Alice", "Anna"}

    def test_unknown_gender_returns_doe(self, names_db):
        assert names_db.pick_random("unknown", "a") == "Doe"

    def test_none_gender_returns_doe(self, names_db):
        assert names_db.pick_random(None, "a") == "Doe"

    def test_none_first_char_returns_doe(self, names_db):
        assert names_db.pick_random("female", None) == "Doe"

    def test_missing_letter_returns_doe(self, names_db):
        assert names_db.pick_random("female", "z") == "Doe"

    def test_uppercase_first_char_is_normalised(self, names_db):
        # pick_random uses first_char.lower() internally
        assert names_db.pick_random("female", "A") in {"Alice", "Anna"}

    def test_empty_db_returns_doe(self, tmp_path):
        db = NameDatabase(str(tmp_path))
        assert db.pick_random("female", "a") == "Doe"
