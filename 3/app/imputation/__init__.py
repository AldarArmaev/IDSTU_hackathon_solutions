from ..series import parse_timestamp, require_number


METHODS = {"constant", "ffill", "bfill", "linear"}
MISSING_REFERENCE = {
    "ffill": "no_previous_value",
    "bfill": "no_next_value",
    "linear": "no_reference_point",
}


def directional_fill(column, indices):
    reference = None
    for index in indices:
        if column[index] is None:
            column[index] = reference
        else:
            reference = column[index]


def linear_fill(column, times):
    known = [index for index, value in enumerate(column) if value is not None]
    for left, right in zip(known, known[1:]):
        duration = (times[right] - times[left]).total_seconds()
        if duration == 0:
            continue
        for index in range(left + 1, right):
            weight = (times[index] - times[left]).total_seconds() / duration
            column[index] = (1 - weight) * column[left] + weight * column[right]


def impute(dataset, method, parameters, names):
    timestamps = dataset["timestamps"]
    values = dataset["values"].copy()
    times = [parse_timestamp(value) for value in timestamps] if method == "linear" else []
    if method == "constant":
        replacement = require_number(parameters.get("value", 0), "value")

    warnings = []
    filled_values = 0
    for name in names:
        column = values[name].copy()
        missing = [index for index, value in enumerate(column) if value is None]
        if method == "constant":
            for index in missing:
                column[index] = replacement
        elif method == "linear":
            linear_fill(column, times)
        else:
            indices = range(len(column))
            directional_fill(column, reversed(indices) if method == "bfill" else indices)

        for index in missing:
            if column[index] is None:
                warnings.append({"method": method, "variable": name, "index": index,
                                 "reason": MISSING_REFERENCE[method]})
            else:
                filled_values += 1
        values[name] = column

    report = {
        "filled_values": filled_values,
        "remaining_nulls": sum(value is None for column in values.values() for value in column),
    }
    return {"timestamps": timestamps, "values": values}, report, warnings
