import json
import re
from datetime import datetime
from math import isfinite
from pathlib import Path


def solve(data):
    timestamps = data["dataset"]["timestamps"]
    values = data["dataset"]["values"]
    if not isinstance(timestamps, list) or not isinstance(values, dict):
        raise ValueError

    seen = set()
    duplicates, out_of_order = [], []
    for i, timestamp in enumerate(timestamps):
        if not isinstance(timestamp, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}", timestamp
        ):
            raise ValueError
        datetime.fromisoformat(timestamp)
        if timestamp in seen:
            duplicates.append(i)
        if i and timestamp < timestamps[i - 1]:
            out_of_order.append(i)
        seen.add(timestamp)

    missing = {}
    for name, column in values.items():
        if not isinstance(column, list) or len(column) != len(timestamps):
            raise ValueError
        indices = []
        for i, value in enumerate(column):
            if value is None:
                indices.append(i)
            elif type(value) is not int and (type(value) is not float or not isfinite(value)):
                raise ValueError
        if indices:
            missing[name] = indices

    return {"missing_values": missing, "duplicate_timestamp_indices": duplicates,
            "timestamps_out_of_order_indices": out_of_order}


if __name__ == "__main__":
    try:
        result = solve(json.loads(Path("input.json").read_text(encoding="utf-8-sig")))
    except (OSError, ValueError, TypeError, KeyError):
        result = {"status": "error", "message": "format data error"}
    Path("output.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
