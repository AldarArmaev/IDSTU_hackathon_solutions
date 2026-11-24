from csv import Error as CsvError
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .aggregation import OPERATIONS, aggregate
from .formats import MEDIA_TYPES, read_dataset, write_dataset
from .imputation import METHODS as IMPUTATION_METHODS, impute
from .normalization import METHODS as NORMALIZATION_METHODS, normalize
from .quality import check
from .series import select_variables, validate_dataset


app = FastAPI(title="Обработка временных рядов", docs_url=None, redoc_url=None)
app.mount("/swagger", StaticFiles(directory=Path(__file__).with_name("static")), name="swagger")


class Dataset(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)

    timestamps: list[str]
    values: dict[str, list[int | float | None]]

    @model_validator(mode="after")
    def validate_rows(self):
        validate_dataset(self.model_dump())
        return self


class ProcessRequest(BaseModel):
    dataset: Dataset
    method: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ProcessResult(BaseModel):
    dataset: Dataset
    report: dict[str, Any]
    warnings: list[dict[str, Any]]


class ConvertedDataset(BaseModel):
    dataset: Dataset
    report: dict[str, Any]


@app.exception_handler(RequestValidationError)
async def invalid_schema(request, exc):
    detail = "; ".join(f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
                       for error in exc.errors())
    return JSONResponse({"detail": detail}, status_code=422)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="Обработка временных рядов",
        swagger_js_url="/swagger/swagger-ui-bundle.js",
        swagger_css_url="/swagger/swagger-ui.css",
        swagger_favicon_url="/swagger/favicon-32x32.png",
        swagger_ui_parameters={"validatorUrl": None},
    )


@app.post("/api/v1/process", response_model=ProcessResult)
def process(request: ProcessRequest):
    dataset = request.dataset.model_dump()
    method, parameters = request.method, request.parameters
    warnings = []
    try:
        names = select_variables(dataset, parameters)
        if method == "check":
            findings = check(dataset)
            issues = [{"type": "missing", "variable": name, "index": index}
                      for name, indices in findings["missing_values"].items() if name in names
                      for index in indices]
            issues += [{"type": "duplicate", "index": index}
                       for index in findings["duplicate_timestamp_indices"]]
            issues += [{"type": "out_of_order", "index": index}
                       for index in findings["timestamps_out_of_order_indices"]]
            report = {"issues": issues}
        elif method in IMPUTATION_METHODS:
            dataset, report, warnings = impute(dataset, method, parameters, names)
        elif method in OPERATIONS:
            interval = parameters.get("interval", "1d")
            if dataset["timestamps"] != sorted(dataset["timestamps"]):
                raise ValueError("aggregation requires ordered timestamps")
            dataset = aggregate(dataset, method, interval, names)
            report = {"method": method, "interval": interval, "rows": len(dataset["timestamps"])}
        elif method in NORMALIZATION_METHODS:
            dataset, report = normalize(dataset, method, parameters.get("coefficient", 1), names)
        else:
            raise ValueError("unknown method")
        validate_dataset(dataset)
    except (ValueError, OverflowError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"dataset": dataset, "report": report, "warnings": warnings}


@app.post("/api/v1/convert", response_model=ConvertedDataset, responses={
    200: {"content": {MEDIA_TYPES[kind]: {"schema": {"type": "string", "format": "binary"}}
                      for kind in ("csv", "xlsx")}},
})
def convert(file: UploadFile | None = File(None), target_format: str = Form(...),
            delimiter: str = Form(",")):
    if file is None:
        raise HTTPException(400, "missing file")
    source_format = Path(file.filename or "").suffix[1:].lower()
    if source_format not in MEDIA_TYPES:
        raise HTTPException(400, "unsupported file extension")
    if target_format not in MEDIA_TYPES:
        raise HTTPException(400, "unsupported target format")
    try:
        dataset = read_dataset(file.file.read(), source_format, delimiter)
        if target_format == "json":
            return {"dataset": dataset,
                    "report": {"rows": len(dataset["timestamps"]), "target_format": "json"}}
        content = write_dataset(dataset, target_format, delimiter)
    except (ValueError, OverflowError, CsvError, BadZipFile, InvalidFileException,
            ParseError, OSError, TypeError, IndexError, KeyError) as exc:
        raise HTTPException(400, f"invalid {source_format} data: {exc}") from exc
    return Response(content, media_type=MEDIA_TYPES[target_format],
                    headers={"Content-Disposition": f'attachment; filename="output.{target_format}"'})
