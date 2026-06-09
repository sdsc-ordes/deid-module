import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(tmp_path, monkeypatch, names_db_path):
    monkeypatch.setenv("SURROGATE_MAP_FILE", str(tmp_path / "map.json"))
    monkeypatch.setenv("SURROGATE_NAMES_DB_FILE", str(names_db_path))
    with TestClient(app) as c:
        yield c


def test_response_schema(client):
    resp = client.post("/pii", json={"pii": "test@example.com", "entity_type": "CONTACT"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"pii", "entity_type", "surrogate"}
    assert data["pii"] == "test@example.com"
    assert data["entity_type"] == "CONTACT"


def test_date_year_is_shifted_by_default_offset(client):
    resp = client.post("/pii", json={"pii": "01/01/2020", "entity_type": "DATE"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] == "01/01/2023"


def test_unknown_entity_type_returns_redacted(client):
    resp = client.post("/pii", json={"pii": "anything", "entity_type": "UNKNOWN_TYPE"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] == "REDACTED"


@pytest.mark.parametrize("pii,entity_type,expected", [
    ("Swiss", "NATIONALITY", "Nationality-UNKNOWN"),
    ("Married", "CIVILSTATUS", "CivilStatus-UNKNOWN"),
    ("Engineer", "PROFESSION", "Profession-UNKNOWN"),
    ("Sister", "PERSONALRELATIONSHIP", "Relationship-UNKNOWN"),
    ("CHUV", "ORGANIZATION", "Organization-UNKNOWN"),
])
def test_fixed_string_surrogates(client, pii, entity_type, expected):
    resp = client.post("/pii", json={"pii": pii, "entity_type": entity_type})
    assert resp.json()["surrogate"] == expected


def test_surrogate_is_idempotent(client):
    payload = {"pii": "01/01/2020", "entity_type": "DATE"}
    r1 = client.post("/pii", json=payload)
    r2 = client.post("/pii", json=payload)
    assert r1.json()["surrogate"] == r2.json()["surrogate"]


def test_name_surrogate_uses_names_db(client):
    resp = client.post("/pii", json={"pii": "Alice", "entity_type": "NAME"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] in {"Alice", "Anna"}
