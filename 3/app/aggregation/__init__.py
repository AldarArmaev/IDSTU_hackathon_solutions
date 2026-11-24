from itertools import groupby
from statistics import mean


OPERATIONS = {"mean": mean, "min": min, "max": max, "sum": sum}


def aggregate(dataset, method, interval, names):
    if interval != "1d":
        raise ValueError("interval must be 1d")
    timestamps = dataset["timestamps"]
    if not timestamps:
        return {"timestamps": [], "values": {}}

    operation = OPERATIONS[method]
    input_values = dataset["values"]
    result = {"timestamps": [], "values": {name: [] for name in names}}
    for day, rows in groupby(range(len(timestamps)), key=lambda index: timestamps[index][:10]):
        indices = list(rows)
        result["timestamps"].append(day + "T00:00:00")
        for name in names:
            column = input_values[name]
            known = [column[index] for index in indices if column[index] is not None]
            result["values"][name].append(operation(known) if known else None)
    return result
