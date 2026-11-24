import json
from itertools import groupby
from pathlib import Path
from statistics import mean


def solve(data):
    dataset = data["dataset"]
    timestamps, values = dataset["timestamps"], dataset["values"]
    if not timestamps:
        return {"timestamps": [], "values": {}}
    if data["parameters"]["interval"] != "1d":
        raise ValueError("unsupported interval")
    operation = {"mean": mean, "min": min, "max": max, "sum": sum}[data["method"]]
    days, result = [], {name: [] for name in values}
    for day, group in groupby(range(len(timestamps)), key=lambda i: timestamps[i][:10]):
        days.append(day + "T00:00:00")
        indices = list(group)
        for name, column in values.items():
            known = [column[i] for i in indices if column[i] is not None]
            result[name].append(operation(known) if known else None)
    return {"timestamps": days, "values": result}


if __name__ == "__main__":
    data = json.loads(Path("input.json").read_text(encoding="utf-8-sig"))
    Path("output.json").write_text(json.dumps(solve(data), ensure_ascii=False), encoding="utf-8")
