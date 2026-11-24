from math import isfinite
from statistics import mean, pstdev

from ..series import require_number


METHODS = {"minmax", "zscore", "scale"}


def minmax_value(value, minimum, maximum):
    if minimum == maximum:
        return 0.0
    width = maximum - minimum
    if type(width) is float and not isfinite(width):
        return (value / 2 - minimum / 2) / (maximum / 2 - minimum / 2)
    return (value - minimum) / width


def normalize(dataset, method, coefficient, names):
    values = dataset["values"].copy()
    report = {"method": method}
    if method == "scale":
        report["coefficient"] = require_number(coefficient, "coefficient")
    else:
        report["statistics"] = {}

    for name in names:
        column = values[name]
        known = [value for value in column if value is not None]
        if method == "scale":
            values[name] = [value * coefficient if value is not None else None for value in column]
        elif method == "minmax":
            minimum, maximum = min(known, default=None), max(known, default=None)
            report["statistics"][name] = {"min": minimum, "max": maximum}
            values[name] = [minmax_value(value, minimum, maximum) if value is not None else None
                            for value in column]
        else:
            average = mean(known) if known else None
            deviation = pstdev(known) if known else None
            report["statistics"][name] = {"mean": average, "std": deviation}
            values[name] = [((value - average) / deviation if deviation else 0.0)
                            if value is not None else None for value in column]

    return {"timestamps": dataset["timestamps"], "values": values}, report
