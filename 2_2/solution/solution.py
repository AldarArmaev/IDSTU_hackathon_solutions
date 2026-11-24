import json
from math import fsum, prod
from pathlib import Path


def synchronous_time(data, parallel_transfers=False):
    t, q, p, d, w = (data[key] for key in ("t", "q", "p", "d", "w"))
    duration = []
    for i in range(data["k"]):
        transfers = [d[i][j] / w[i][j] for j in range(data["k"])
                     if i != j and p[i][j] == 1 and d[i][j]]
        delay = max(transfers, default=0) if parallel_transfers else sum(transfers)
        duration.append(t[i] + q[i] + delay)
    return sum(max((time for time, active in zip(duration, level) if active == 1), default=0)
               for level in data["S"])


def reliability(data):
    terms = {}
    for variant in data["K"]:
        event = frozenset(tuple(int(index) - 1 for index in token.strip(" ()\t").split("_")[1:])
                          for token in variant.split("&"))
        # P(A ∪ B) = P(A) + P(B) − P(A ∩ B).
        for previous, coefficient in list(terms.items()):
            intersection = previous | event
            terms[intersection] = terms.get(intersection, 0) - coefficient
        terms[event] = terms.get(event, 0) + 1
        terms = {key: value for key, value in terms.items() if value}

    p = data["p"]
    result = fsum(coefficient * prod(p[i][j][k] for i, j, k in event)
                  for event, coefficient in terms.items())
    return min(1, max(0, result))


def solve(data):
    if "K" in data:
        return {"P": reliability(data)}
    return {"T": synchronous_time(data)}


if __name__ == "__main__":
    data = json.loads(Path("input.json").read_text(encoding="utf-8"))
    Path("output.json").write_text(json.dumps(solve(data)), encoding="utf-8")
