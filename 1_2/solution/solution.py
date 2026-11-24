import json
from datetime import datetime
from pathlib import Path


def solve(data):
    dataset = data["dataset"]
    timestamps, values = dataset["timestamps"], dataset["values"]
    method, parameters = data["method"], data.get("parameters", {})
    names = parameters.get("variables", list(values))
    if not isinstance(names, list) or any(name not in values for name in names):
        raise ValueError
    if method == "linear":
        times = [datetime.fromisoformat(timestamp) for timestamp in timestamps]

    result = values.copy()
    for name in names:
        column = values[name].copy()
        if method == "constant":
            value = parameters.get("value", 0)
            if type(value) not in (int, float):
                raise ValueError
            column = [value if cell is None else cell for cell in column]
        elif method in ("ffill", "bfill"):
            order = range(len(column))
            previous = None
            for i in reversed(order) if method == "bfill" else order:
                if column[i] is None:
                    column[i] = previous
                else:
                    previous = column[i]
        elif method == "linear":
            known = [i for i, value in enumerate(column) if value is not None]
            for left, right in zip(known, known[1:]):
                duration = (times[right] - times[left]).total_seconds()
                if duration:
                    for i in range(left + 1, right):
                        weight = (times[i] - times[left]).total_seconds() / duration
                        column[i] = (1 - weight) * column[left] + weight * column[right]
        result[name] = column
    return {"timestamps": timestamps, "values": result}


if __name__ == "__main__":
    try:
        result = solve(json.loads(Path("input.json").read_text(encoding="utf-8-sig")))
        output = json.dumps(result, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, KeyError, OSError, OverflowError):
        output = json.dumps({"status": "error", "message": "format data error"})
    Path("output.json").write_text(output, encoding="utf-8")
