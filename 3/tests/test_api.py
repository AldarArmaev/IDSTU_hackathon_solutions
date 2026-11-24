import json
from datetime import datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app.main import app


client = TestClient(app)
PROCESS = "/api/v1/process"
CONVERT = "/api/v1/convert"
TIMESTAMPS = ["2016-01-01T02:00:00", "2016-01-01T05:00:00", "2016-01-01T15:00:00"]
COLUMNS = ["temperature_c", "pressure_mmhg", "wind_speed_ms", "relative_humidity_pct"]


def process(method, values, parameters=None, timestamps=TIMESTAMPS):
    data = {"method": method, "dataset": {"timestamps": timestamps, "values": values}}
    if parameters is not None:
        data["parameters"] = parameters
    return client.post(PROCESS, json=data)


def test_service_routes():
    assert client.get("/health").json() == {"status": "ok"}
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "/swagger/swagger-ui-bundle.js" in docs.text
    assert client.get("/swagger/swagger-ui-bundle.js").status_code == 200
    assert {PROCESS, CONVERT, "/health"} <= client.get("/openapi.json").json()["paths"].keys()


def test_check():
    timestamps = [TIMESTAMPS[0], TIMESTAMPS[2], TIMESTAMPS[0]]
    values = {"x": [0, None, 1]}
    response = process("check", values, timestamps=timestamps)
    assert response.status_code == 200
    assert response.json() == {
        "dataset": {"timestamps": timestamps, "values": values},
        "report": {"issues": [{"type": "missing", "variable": "x", "index": 1},
                              {"type": "duplicate", "index": 2},
                              {"type": "out_of_order", "index": 2}]},
        "warnings": [],
    }


@pytest.mark.parametrize("method, expected", [
    ("constant", [0, 0, 13]), ("ffill", [0, 0, 13]),
    ("bfill", [0, 13, 13]), ("linear", [0, 3, 13]),
])
def test_imputation(method, expected):
    response = process(method, {"x": [0, None, 13], "y": [None, 2, 3]}, {"variables": ["x"]})
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"] == {"timestamps": TIMESTAMPS, "values": {"x": expected, "y": [None, 2, 3]}}
    assert body["report"] == {"filled_values": 1, "remaining_nulls": 1}
    assert body["warnings"] == []


@pytest.mark.parametrize("method, index, reason", [
    ("ffill", 0, "no_previous_value"), ("bfill", 2, "no_next_value"),
    ("linear", 0, "no_reference_point"),
])
def test_missing_reference(method, index, reason):
    body = process(method, {"x": [None, 7, None]}).json()
    assert body["dataset"]["values"]["x"][index] is None
    assert {"method": method, "variable": "x", "index": index, "reason": reason} in body["warnings"]


@pytest.mark.parametrize("method, expected", [("mean", 3), ("min", 2), ("max", 4), ("sum", 6)])
def test_daily_aggregation(method, expected):
    response = process(method, {"x": [2, 4, None]}, timestamps=TIMESTAMPS[:2] + ["2016-01-03T00:00:00"])
    assert response.status_code == 200
    assert response.json() == {
        "dataset": {"timestamps": ["2016-01-01T00:00:00", "2016-01-03T00:00:00"],
                    "values": {"x": [expected, None]}},
        "report": {"method": method, "interval": "1d", "rows": 2},
        "warnings": [],
    }


@pytest.mark.parametrize("method, expected, report", [
    ("minmax", [0, 1], {"min": 2, "max": 6}),
    ("zscore", [-1, 1], {"mean": 4, "std": 2}),
    ("scale", [2, 6], None),
])
def test_normalization(method, expected, report):
    response = process(method, {"x": [2, None, 6], "y": [3, None, 3], "z": [None] * 3})
    assert response.status_code == 200
    body = response.json()
    result = body["dataset"]["values"]
    assert [result["x"][0], result["x"][2]] == pytest.approx(expected, abs=1e-6)
    assert result["x"][1] is None and result["z"] == [None] * 3
    assert result["y"] == ([3, None, 3] if method == "scale" else [0, None, 0])
    if report is None:
        assert body["report"]["coefficient"] == 1
    else:
        assert body["report"]["statistics"]["x"] == report


@pytest.mark.parametrize("method, values, params, timestamps, status", [
    ("bogus", {"x": [1, 2, 3]}, {}, TIMESTAMPS, 400),
    ("constant", {"x": [None, 1, 2]}, {"variables": ["missing"]}, TIMESTAMPS, 400),
    ("check", {"x": [True, 2, 3]}, {}, TIMESTAMPS, 422),
    ("check", {"x": [1, 2]}, {}, TIMESTAMPS, 422),
    ("check", {"x": [1]}, {}, ["2016-01-01T02:00:00Z"], 422),
])
def test_invalid_process(method, values, params, timestamps, status):
    response = process(method, values, params, timestamps)
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("source,target", [
    ("csv", "json"), ("csv", "xlsx"), ("xlsx", "csv"),
    ("xlsx", "json"), ("json", "csv"), ("json", "xlsx"),
])
def test_conversion(source, target):
    timestamp = TIMESTAMPS[0]
    cells = [2.5, None, 1, 80]
    expected = {"timestamps": [timestamp], "values": {name: [cell] for name, cell in zip(COLUMNS, cells)}}
    if source == "csv":
        content = ("extra;" + ";".join(["timestamp", *COLUMNS]) + f"\nignore;{timestamp};2.5;;1;80\n").encode()
    elif source == "xlsx":
        workbook = Workbook()
        workbook.active.append(["timestamp", *COLUMNS])
        workbook.active.append([datetime.fromisoformat(timestamp), *cells])
        stream = BytesIO()
        workbook.save(stream)
        content = stream.getvalue()
    else:
        content = json.dumps(expected).encode()

    response = client.post(CONVERT, data={"target_format": target, "delimiter": ";"},
                           files={"file": (f"source.{source}", content)})
    assert response.status_code == 200
    if target == "json":
        assert response.json() == {"dataset": expected, "report": {"rows": 1, "target_format": "json"}}
    else:
        assert f'filename="output.{target}"' in response.headers["Content-Disposition"]
        if target == "csv":
            assert response.headers["Content-Type"].startswith("text/csv")
            assert response.text.splitlines()[1] == f"{timestamp};2.5;;1;80"
        else:
            with BytesIO(response.content) as stream:
                workbook = load_workbook(stream)
                assert len(workbook.worksheets) == 1
                assert list(workbook.active.values)[1] == (timestamp, *cells)
                workbook.close()


@pytest.mark.parametrize("file,target", [
    (None, "json"), (("a.txt", b""), "json"),
    (("a.csv", b"timestamp"), "json"), (("a.xlsx", b"bad zip"), "json"),
    (("a.csv", b""), "txt"),
])
def test_invalid_conversion(file, target):
    response = client.post(CONVERT, data={"target_format": target}, files={"file": file} if file else None)
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)
