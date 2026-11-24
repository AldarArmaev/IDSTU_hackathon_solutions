# Обработка временных рядов

FastAPI-сервис для проверки данных, заполнения пропусков, суточного агрегирования, нормализации и конвертации CSV, XLSX и JSON.

## Запуск

Нужен Python 3.11 или новее. Выполните команды из папки проекта. Команда активации для PowerShell — `.\.venv\Scripts\Activate.ps1`, для Linux и macOS — `source .venv/bin/activate`.

```sh
python -m venv .venv
# Активируйте окружение командой для вашей системы.
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка доступности — `http://127.0.0.1:8000/health`. Интерактивная документация открывается на `http://127.0.0.1:8000/docs`, схема OpenAPI доступна на `/openapi.json`. Ресурсы Swagger UI находятся в `app/static/`.

## Структура

- `app/main.py` содержит маршруты и модели запросов.
- `app/quality/`, `app/imputation/`, `app/aggregation/`, `app/normalization/` и `app/formats/` содержат обработку данных.
- `app/series.py` проверяет метки времени, значения и выбор переменных.
- `tests/` содержит тесты HTTP-интерфейса.

## POST /api/v1/process

Передайте JSON с `dataset`, `method` и необязательным `parameters`. Ряд состоит из списка меток `timestamps` и объекта `values`. Метки записываются как `YYYY-MM-DDTHH:MM:SS`, а пропуски — как `null`.

| Методы | Параметры | Действие |
| --- | --- | --- |
| `check` | — | Ищет пропуски, повторы меток и нарушения порядка |
| `constant` | `value`, по умолчанию `0` | Заполняет пропуски числом |
| `ffill`, `bfill` | — | Берёт известное значение слева или справа |
| `linear` | — | Интерполирует между опорными точками по времени |
| `mean`, `min`, `max`, `sum` | `interval`, по умолчанию `1d` | Считает статистику по календарным суткам |
| `minmax`, `zscore` | — | Нормализует непустые значения отдельно для каждой переменной, `zscore` использует `ddof=0` |
| `scale` | `coefficient`, по умолчанию `1` | Умножает непустые значения на коэффициент |

`parameters.variables` выбирает переменные. Для агрегирования набор столбцов результата состоит из выбранных переменных. Для проверки качества выбор ограничивает поиск пропусков. Для заполнения и нормализации остальные столбцы сохраняются. При заполнении пропуск без опорной точки остаётся `null` и попадает в `warnings`.

Пример запроса и ответа для заполнения пропуска.

```json
{
  "dataset": {"timestamps": ["2016-01-01T02:00:00"], "values": {"temperature_c": [null]}},
  "method": "constant",
  "parameters": {"value": 5}
}
```

```json
{
  "dataset": {"timestamps": ["2016-01-01T02:00:00"], "values": {"temperature_c": [5]}},
  "report": {"filled_values": 1, "remaining_nulls": 0},
  "warnings": []
}
```

## POST /api/v1/convert

Отправьте `multipart/form-data` с полями `file`, `target_format` и, при необходимости, `delimiter`. Поддерживаются `csv`, `xlsx` и `json`, исходный формат определяется по расширению. Ответ для JSON содержит `dataset` и `report`. Для CSV и XLSX сервис отдаёт файл.

```sh
curl -F 'file=@source.csv' -F 'target_format=json' http://127.0.0.1:8000/api/v1/convert
```

CSV и XLSX используют заголовки `timestamp`, `temperature_c`, `pressure_mmhg`, `wind_speed_ms`, `relative_humidity_pct`. Обработка ошибок возвращает JSON с `detail` и кодом 400 или 422.

## Тесты и ограничения

```sh
pytest -q
```

Тесты используют `TestClient` и работают без запущенного сервера. Агрегирование поддерживает календарные сутки и требует упорядоченных меток. XLSX поддерживает один лист. Конвертация обрабатывает файлы в памяти и использует стандартную точность чисел XLSX.
