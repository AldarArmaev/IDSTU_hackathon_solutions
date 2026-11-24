from datetime import datetime
from math import isfinite
from re import compile


TIMESTAMP = compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")


def parse_timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError("timestamps must have the form YYYY-MM-DDTHH:MM:SS")
    return datetime.fromisoformat(value)


def is_number(value):
    return type(value) is int or (type(value) is float and isfinite(value))


def require_number(value, name):
    if not is_number(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def validate_dataset(dataset):
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be an object")
    timestamps = dataset.get("timestamps")
    values = dataset.get("values")
    if not isinstance(timestamps, list) or not isinstance(values, dict):
        raise ValueError("dataset requires timestamps and values")
    for timestamp in timestamps:
        parse_timestamp(timestamp)
    for name, column in values.items():
        if not isinstance(column, list) or len(column) != len(timestamps):
            raise ValueError(f"{name} must have the same length as timestamps")
        if any(value is not None and not is_number(value) for value in column):
            raise ValueError(f"{name} must contain only finite numbers or null")
    return {"timestamps": timestamps, "values": values}


def select_variables(dataset, parameters):
    values = dataset["values"]
    names = parameters.get("variables", list(values))
    if not isinstance(names, list) or any(
        not isinstance(name, str) or name not in values for name in names
    ):
        raise ValueError("variables must be a list of existing variable names")
    return tuple(dict.fromkeys(names))
