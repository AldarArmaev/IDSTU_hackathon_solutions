import json
from fractions import Fraction
from graphlib import TopologicalSorter
from math import ceil
from pathlib import Path


def matrix(data, name, height, width, binary=False):
    rows = data[name]
    if not isinstance(rows, list) or len(rows) != height:
        raise ValueError(name)
    for row in rows:
        if not isinstance(row, list) or len(row) != width:
            raise ValueError(name)
        for cell in row:
            if binary:
                if type(cell) is not int or cell not in (0, 1):
                    raise ValueError(name)
            elif type(cell) not in (float, int) or not cell >= 0:
                raise ValueError(name)
    return rows


def clock(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def solve(data, only_node=None):
    n, z, k = (data[key] for key in ("n", "z", "k"))
    if any(type(x) is not int or x < 1 for x in (n, z, k)):
        raise ValueError("invalid dimensions")
    t = matrix(data, "t", k, n)
    a = matrix(data, "A", n, z, binary=True)
    b = matrix(data, "B", n, z, binary=True)
    d = matrix(data, "D", n, n)
    w = matrix(data, "W", k, k)
    inputs = [{index for index, bit in enumerate(row) if bit} for row in a]
    outputs = [{index for index, bit in enumerate(row) if bit} for row in b]
    parents = {child: [parent for parent in range(n) if outputs[parent] & inputs[child]]
               for child in range(n)}
    edges = [(parent, child) for child, incoming in parents.items() for parent in incoming]
    if not any(d[parent][child] for parent, child in edges):
        d = list(zip(*d))

    slots = {f"node{node + 1}": [] for node in range(k)}
    available = [0] * k
    finished = {}
    nodes = range(k) if only_node is None else (only_node,)
    for child in TopologicalSorter(parents).static_order():
        candidates = []
        for node in nodes:
            start = available[node]
            for parent in parents[child]:
                source, end = finished[parent]
                size = d[parent][child] if source != node else 0
                if size and not w[source][node]:
                    break
                delay = ceil(Fraction(str(size)) / Fraction(str(w[source][node]))) if size else 0
                start = max(start, end + delay)
            else:
                candidates.append((start + ceil(t[node][child]), start, node))

        if not candidates:
            fastest_node = min(range(k), key=lambda node: sum(t[node]))
            return solve(data, fastest_node)
        end, start, node = min(candidates)
        available[node] = end
        finished[child] = node, end
        slots[f"node{node + 1}"].append([f"m{child + 1}", clock(start), clock(end)])

    return {"DAG": [{"parent": f"m{parent + 1}", "child": f"m{child + 1}"}
                    for parent, child in sorted(edges)], "schedule": slots}


if __name__ == "__main__":
    try:
        data = json.loads(Path("input.json").read_text(encoding="utf-8"))
        result = solve(data)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        result = {"message": "format data error", "status": "error"}
    Path("output.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
