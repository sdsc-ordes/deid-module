import json

import pytest
from fastapi.testclient import TestClient

from main import app

JSONL_MEDIA_TYPE = "application/jsonl"


@pytest.fixture
def client(tmp_path, monkeypatch, names_db_path):
    monkeypatch.setenv("SURROGATE_MAP_FILE", str(tmp_path / "map.json"))
    monkeypatch.setenv("SURROGATE_NAMES_DB_FILE", str(names_db_path))
    with TestClient(app) as c:
        yield c


@pytest.fixture(params=[
    pytest.param(("map.json"), id="json"),
    pytest.param(("map.db"), id="sqlite"),
])
def map_client(request, tmp_path, monkeypatch, names_db_path):
    filename = request.param
    monkeypatch.setenv("SURROGATE_MAP_FILE", str(tmp_path / filename))
    monkeypatch.setenv("SURROGATE_NAMES_DB_FILE", str(names_db_path))
    with TestClient(app) as c:
        yield c


def test_response_schema(client):
    resp = client.post("/pii", json={"value": "test@example.com", "entity_type": "CONTACT"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"pii", "surrogate"}
    assert data["pii"] == {"value": "test@example.com", "entity_type": "CONTACT"}


def test_date_year_is_shifted_by_default_offset(client):
    resp = client.post("/pii", json={"value": "01/01/2020", "entity_type": "DATE"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] == "01/01/2023"


def test_unknown_entity_type_returns_redacted(client):
    resp = client.post("/pii", json={"value": "anything", "entity_type": "UNKNOWN_TYPE"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] == "REDACTED"


@pytest.mark.parametrize("value,entity_type,expected", [
    ("Swiss", "NATIONALITY", "Nationality-UNKNOWN"),
    ("Married", "CIVILSTATUS", "CivilStatus-UNKNOWN"),
    ("Engineer", "PROFESSION", "Profession-UNKNOWN"),
    ("Sister", "PERSONALRELATIONSHIP", "Relationship-UNKNOWN"),
    ("CHUV", "ORGANIZATION", "Organization-UNKNOWN"),
])
def test_fixed_string_surrogates(client, value, entity_type, expected):
    resp = client.post("/pii", json={"value": value, "entity_type": entity_type})
    assert resp.json()["surrogate"] == expected


def test_surrogate_is_idempotent(client):
    payload = {"value": "01/01/2020", "entity_type": "DATE"}
    r1 = client.post("/pii", json=payload)
    r2 = client.post("/pii", json=payload)
    assert r1.json()["surrogate"] == r2.json()["surrogate"]


def test_name_surrogate_uses_names_db(client):
    resp = client.post("/pii", json={"value": "Alice", "entity_type": "NAME"})
    assert resp.status_code == 200
    assert resp.json()["surrogate"] in {"Alice", "Anna"}


def _parse_jsonl(resp):
    return [json.loads(line) for line in resp.text.splitlines() if line]


def test_map_empty(map_client):
    resp = map_client.get("/map")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(JSONL_MEDIA_TYPE)
    assert resp.text == ""


def test_map_streams_inserted_entries(map_client):
    map_client.post("/pii", json={"value": "01/01/2020", "entity_type": "DATE"})
    map_client.post("/pii", json={"value": "Engineer", "entity_type": "PROFESSION"})

    resp = map_client.get("/map")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(JSONL_MEDIA_TYPE)
    by_value = {item["pii"]["value"]: item for item in _parse_jsonl(resp)}
    assert by_value["01/01/2020"] == {
        "pii": {"value": "01/01/2020", "entity_type": "DATE"},
        "surrogate": "01/01/2023",
    }
    assert by_value["engineer"] == {
        "pii": {"value": "engineer", "entity_type": "PROFESSION"},
        "surrogate": "Profession-UNKNOWN",
    }


def test_map_streams_incrementally(map_client):
    """Each entry must be flushed as soon as the iterator yields it — no buffering of the full map."""
    for i in range(5):
        map_client.post("/pii", json={"value": f"job-{i}", "entity_type": "PROFESSION"})

    with map_client.stream("GET", "/map") as resp:
        assert resp.status_code == 200
        lines = []
        for line in resp.iter_lines():
            if line:
                lines.append(json.loads(line))
                if len(lines) == 1:
                    break

    assert lines[0]["pii"]["entity_type"] == "PROFESSION"
    assert lines[0]["pii"]["value"].startswith("job-")
