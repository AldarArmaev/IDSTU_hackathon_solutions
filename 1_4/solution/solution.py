import json
from pathlib import Path
from statistics import mean, pstdev


def solve(data):
    dataset = data["dataset"]
    method = data["method"]
    result = {}
    if method == "scale":
        coefficient = data.get("parameters", {}).get("coefficient")
        if type(coefficient) not in (int, float):
            raise ValueError

    for name, column in dataset["values"].items():
        known = [value for value in column if value is not None]
        if not known:
            result[name] = column
        elif method == "scale":
            result[name] = [x * coefficient if x is not None else None for x in column]
        else:
            if method == "minmax":
                center = min(known)
                width = max(known) - center
                if width == float("inf"):
                    divisor = max(known) / 2 - center / 2
                    result[name] = [(x / 2 - center / 2) / divisor if x is not None else None
                                    for x in column]
                    continue
            else:
                center, width = mean(known), pstdev(known)
            result[name] = [((x - center) / width if width else 0.0)
                            if x is not None else None for x in column]
    return {"timestamps": dataset["timestamps"], "values": result}


if __name__ == "__main__":
    try:
        result = solve(json.loads(Path("input.json").read_text(encoding="utf-8-sig")))
        output = json.dumps(result, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, KeyError, OSError, OverflowError):
        output = json.dumps({"status": "error", "message": "format data error"})
    Path("output.json").write_text(output, encoding="utf-8")
