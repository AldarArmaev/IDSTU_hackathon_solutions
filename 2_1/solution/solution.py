import json
from graphlib import TopologicalSorter
from pathlib import Path


def solve(data):
    t, q, p, d, w = (data[key] for key in ("t", "q", "p", "d", "w"))
    parents = {i: [j for j in range(data["k"]) if i != j and p[i][j] == 1]
               for i in range(data["k"])}
    finish = {}
    for i in TopologicalSorter(parents).static_order():
        ready = max((finish[j] + (d[i][j] / w[i][j] if d[i][j] else 0)
                     for j in parents[i]), default=0)
        finish[i] = ready + q[i] + t[i]
    return {"T": max(finish.values(), default=0)}


if __name__ == "__main__":
    data = json.loads(Path("input.json").read_text(encoding="utf-8"))
    Path("output.json").write_text(json.dumps(solve(data)), encoding="utf-8")
