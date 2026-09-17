from __future__ import annotations

from datetime import datetime
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from mixed_timeseries_chart import MixedTimeSeriesChart, TimePoint


class ChartPanel(QWidget):
    """
    Родительский контейнер для MixedTimeSeriesChart.

    Контейнер выше дочернего графика сверху и снизу.
    При наведении мыши на любую область контейнера
    фон дочернего графика становится светлее.
    """

    # Серо-голубой фон родительского контейнера.
    PARENT_BACKGROUND = "#E2EDF9"

    def __init__(
        self,
        area_data: Sequence[TimePoint | tuple[datetime, float]],
        spline_data: Sequence[TimePoint | tuple[datetime, float]],
        line_data: Sequence[TimePoint | tuple[datetime, float]],
        bar_data: Sequence[TimePoint | tuple[datetime, float]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("chartPanel")
        self.setStyleSheet(
            "QWidget#chartPanel {"
            "background-color: #E2EDF9;"
            "border: none;"
            "margin: 0px;"
            "padding: 0px;"
            "}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.chart = MixedTimeSeriesChart(
            area_data=area_data,
            spline_data=spline_data,
            line_data=line_data,
            bar_data=bar_data,
            parent=self,
        )

        layout = QVBoxLayout(self)

        # left, top, right, bottom
        #
        # Родитель выше графика:
        # сверху +56 px, снизу +64 px.
        layout.setContentsMargins(0, 56, 0, 64)
        layout.setSpacing(0)

        layout.addWidget(self.chart)