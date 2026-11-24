import csv
import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook


COLUMNS = ("temperature_c", "pressure_mmhg", "wind_speed_ms", "relative_humidity_pct")
HEADER = ("timestamp", *COLUMNS)


def parse_number(cell):
    if cell is None or cell == "":
        return None
    if isinstance(cell, str):
        try:
            return int(cell)
        except ValueError:
            return float(cell)
    return cell


def read_table(rows):
    header = next(rows)
    indices = [header.index(name) for name in HEADER]
    timestamps = []
    values = {name: [] for name in COLUMNS}
    for row in rows:
        if not row or all(cell in (None, "") for cell in row):
            continue
        cells = [row[i] if i < len(row) else None for i in indices]
        timestamp, *numbers = cells
        timestamps.append(timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp)
        for name, cell in zip(COLUMNS, numbers):
            values[name].append(parse_number(cell))
    return {"timestamps": timestamps, "values": values}


def solve(config):
    source = Path(config["source_file"])
    delimiter = config.get("delimiter", ",")
    if config["source_format"] == "json":
        content = json.loads(source.read_text(encoding="utf-8-sig"))
        dataset = {"timestamps": content["timestamps"], "values": content["values"]}
    elif config["source_format"] == "csv":
        with source.open(encoding="utf-8-sig", newline="") as file:
            dataset = read_table(csv.reader(file, delimiter=delimiter))
    else:
        workbook = load_workbook(source, read_only=True, data_only=True)
        try:
            dataset = read_table(workbook.worksheets[0].values)
        finally:
            workbook.close()

    target = config["target_format"]
    if target == "json":
        Path("output.json").write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
        return
    timestamps, values = dataset["timestamps"], dataset["values"]
    rows = zip(timestamps, *(values.get(name, [None] * len(timestamps)) for name in COLUMNS))
    if target == "csv":
        with Path("output.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=delimiter)
            writer.writerow(HEADER)
            writer.writerows(rows)
    else:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("data")
        sheet.append(HEADER)
        for row in rows:
            sheet.append(row)
        workbook.save("output.xlsx")


if __name__ == "__main__":
    solve(json.loads(Path("input.json").read_text(encoding="utf-8-sig")))
