"""Tests for session-scoped surrogate generation.

A surrogate is scoped to its ``session`` (e.g. a document): the same PII value
gets a stable surrogate within a session, but is independent across sessions.
"""

from generator import (
    generate_date_surrogate,
    generate_name_surrogate,
    generate_number_surrogate,
)
from models import Pii


def _name(value: str, session: str | None = None) -> Pii:
    return Pii(value=value, entity_type="NAME", session=session)


class TestNameSessionScoping:
    def test_surrogate_is_stored_under_its_session(self, json_map, names_db):
        pii = _name("Steve", session="doc1")
        surrogate = generate_name_surrogate(pii, json_map, names_db)
        assert json_map.get(_name("Steve", session="doc1")) == surrogate

    def test_surrogate_is_not_visible_to_another_session(self, json_map, names_db):
        generate_name_surrogate(_name("Steve", session="doc1"), json_map, names_db)
        assert json_map.get(_name("Steve", session="doc2")) is None

    def test_surrogate_is_stable_within_a_session(self, json_map, names_db):
        first = generate_name_surrogate(_name("Steve", session="doc1"), json_map, names_db)
        second = generate_name_surrogate(_name("Steve", session="doc1"), json_map, names_db)
        assert first == second

    def test_same_value_in_two_sessions_is_independent(self, json_map, names_db):
        generate_name_surrogate(_name("Steve", session="doc1"), json_map, names_db)
        generate_name_surrogate(_name("Steve", session="doc2"), json_map, names_db)
        sessions = {item.pii.session for item in json_map}
        assert {"doc1", "doc2"} <= sessions


class TestNumberSessionScoping:
    def test_surrogate_is_scoped_by_session(self, json_map):
        pii = Pii(value="12345", entity_type="PATIENTID", session="doc1")
        surrogate = generate_number_surrogate(pii, json_map)
        # number surrogates are cached under a NUMBER entity type, scoped per session
        assert json_map.get(Pii(value="12345", entity_type="NUMBER", session="doc1")) == surrogate
        assert json_map.get(Pii(value="12345", entity_type="NUMBER", session="doc2")) is None


class TestDateSessionScoping:
    def test_surrogate_is_scoped_by_session(self, json_map):
        pii = Pii(value="01/01/2020", entity_type="DATE", session="doc1")
        surrogate = generate_date_surrogate(pii, json_map, year_shift=3)
        assert json_map.get(Pii(value="01/01/2020", entity_type="DATE", session="doc1")) == surrogate
        assert json_map.get(Pii(value="01/01/2020", entity_type="DATE", session="doc2")) is None
