import csv
import json
from datetime import datetime
from io import BytesIO, StringIO

from openpyxl import Workbook, load_workbook

from ..series import validate_dataset


COLUMNS = ("temperature_c", "pressure_mmhg", "wind_speed_ms", "relative_humidity_pct")
HEADER = ("timestamp", *COLUMNS)
MEDIA_TYPES = {
    "json": "application/json",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validate_delimiter(delimiter):
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '\r\n\0"':
        raise ValueError("delimiter must be one CSV separator character")


def number(cell):
    if cell is None or isinstance(cell, str) and not cell.strip():
        return None
    if isinstance(cell, str):
        try:
            return int(cell)
        except ValueError:
            return float(cell)
    return cell


def table_to_dataset(rows):
    header = next(rows, ())
    if any(header.count(name) != 1 for name in HEADER):
        raise ValueError("table must have timestamp and all four weather columns")
    positions = [header.index(name) for name in HEADER]
    timestamps, values = [], {name: [] for name in COLUMNS}
    for row in rows:
        if not row or all(cell is None or cell == "" for cell in row):
            continue
        cells = [row[index] if index < len(row) else None for index in positions]
        timestamp, *measurements = cells
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        timestamps.append(timestamp)
        for name, cell in zip(COLUMNS, measurements):
            values[name].append(number(cell))
    return validate_dataset({"timestamps": timestamps, "values": values})


def read_dataset(content, source_format, delimiter=","):
    if source_format == "json":
        return validate_dataset(json.loads(content.decode("utf-8-sig")))
    if source_format == "csv":
        validate_delimiter(delimiter)
        text = StringIO(content.decode("utf-8-sig"), newline="")
        return table_to_dataset(csv.reader(text, delimiter=delimiter, strict=True))
    if source_format == "xlsx":
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            if len(workbook.worksheets) != 1:
                raise ValueError("XLSX must have one sheet")
            return table_to_dataset(workbook.worksheets[0].values)
        finally:
            workbook.close()
    raise ValueError("unsupported source format")


def dataset_rows(dataset):
    yield HEADER
    columns = dataset["values"]
    timestamps = dataset["timestamps"]
    empty = [None] * len(timestamps)
    yield from zip(timestamps, *(columns.get(name, empty) for name in COLUMNS))


def write_dataset(dataset, target_format, delimiter=","):
    if target_format == "json":
        return json.dumps(dataset, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if target_format == "csv":
        validate_delimiter(delimiter)
        text = StringIO(newline="")
        csv.writer(text, delimiter=delimiter).writerows(dataset_rows(dataset))
        return text.getvalue().encode("utf-8")
    if target_format == "xlsx":
        stream = BytesIO()
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("data")
        for row in dataset_rows(dataset):
            sheet.append(row)
        workbook.save(stream)
        return stream.getvalue()
    raise ValueError("unsupported target format")
