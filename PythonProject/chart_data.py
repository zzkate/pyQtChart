from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mixed_timeseries_chart import TimePoint


def load_series(file_path: Path) -> list[TimePoint]:
    """
    Загружает одну серию из JSON-файла.

    Ожидаемый формат:
    [
      {"time": "2026-06-07", "value": 10.0}
    ]
    """
    try:
        raw_data = json.loads(
            file_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Не найден файл с данными: {file_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Некорректный JSON в файле: {file_path}"
        ) from error

    if not isinstance(raw_data, list):
        raise ValueError(
            f"Файл {file_path.name} должен содержать JSON-массив."
        )

    result: list[TimePoint] = []

    for index, item in enumerate(raw_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"{file_path.name}, строка {index}: "
                "ожидается объект с полями time и value."
            )

        try:
            timestamp = datetime.fromisoformat(item["time"])
            value = float(item["value"])
        except KeyError as error:
            raise ValueError(
                f"{file_path.name}, строка {index}: "
                f"отсутствует поле {error.args[0]!r}."
            ) from error
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{file_path.name}, строка {index}: "
                "time должен иметь формат YYYY-MM-DD, "
                "а value должен быть числом."
            ) from error

        result.append(
            TimePoint(
                time=timestamp,
                value=value,
            )
        )

    if not result:
        raise ValueError(
            f"Файл {file_path.name} не должен быть пустым."
        )

    return result


def load_chart_data(
    data_dir: Path,
) -> tuple[
    list[TimePoint],
    list[TimePoint],
    list[TimePoint],
    list[TimePoint],
]:
    """
    Возвращает данные в порядке, ожидаемом ChartPanel:

    Cost, ROI Confirmed, Conversions, CPA.
    """
    cost = load_series(data_dir / "cost.json")
    roi_confirmed = load_series(
        data_dir / "roi_confirmed.json"
    )
    conversions = load_series(
        data_dir / "conversions.json"
    )
    cpa = load_series(data_dir / "cpa.json")

    return cost, roi_confirmed, conversions, cpa