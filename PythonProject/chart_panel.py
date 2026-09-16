from __future__ import annotations

from datetime import datetime
from typing import Sequence

from PySide6.QtCore import QEvent, Qt
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

    # Когда курсор ВНЕ области ChartPanel:
    # светлый розовый фон дочернего графика.
    NORMAL_CHART_BACKGROUND = "#FCECEF"

    # Когда курсор ВНУТРИ области ChartPanel:
    # более тёмный розовый фон дочернего графика.
    HOVER_CHART_BACKGROUND = "#F9DFE4"

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
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.chart = MixedTimeSeriesChart(
            area_data=area_data,
            spline_data=spline_data,
            line_data=line_data,
            bar_data=bar_data,
            parent=self,
        )

        self.chart.setMouseTracking(True)

        layout = QVBoxLayout(self)

        # left, top, right, bottom
        #
        # Родитель выше графика:
        # сверху +56 px, снизу +64 px.
        layout.setContentsMargins(0, 56, 0, 64)
        layout.setSpacing(0)

        layout.addWidget(self.chart)

        # Нужно отслеживать события как самого контейнера,
        # так и child chart. Иначе при перемещении курсора
        # над дочерним графиком родитель может не получать
        # нужные hover-события.
        self.installEventFilter(self)
        self.chart.installEventFilter(self)

        self._set_chart_hovered(False)

    def _set_chart_hovered(self, hovered: bool) -> None:
        """
        Синхронно меняет все розовые области дочернего графика.

        hovered=False:
            светлый розовый фон.

        hovered=True:
            более тёмный розовый фон.
        """
        color = (
            self.HOVER_CHART_BACKGROUND
            if hovered
            else self.NORMAL_CHART_BACKGROUND
        )

        self.chart.set_surface_color(color)

    def enterEvent(self, event) -> None:
        self._set_chart_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_chart_hovered(False)
        super().leaveEvent(event)

    def eventFilter(self, watched, event) -> bool:
        """
        Поддерживает состояние фона, когда курсор находится
        над дочерним графиком либо над свободным полем родителя.
        """
        if watched is self or watched is self.chart:
            if event.type() == QEvent.Type.Enter:
                self._set_chart_hovered(True)

            elif event.type() == QEvent.Type.Leave:
                cursor_inside_parent = self.rect().contains(
                    self.mapFromGlobal(
                        self.cursor().pos()
                    )
                )

                if not cursor_inside_parent:
                    self._set_chart_hovered(False)

        return super().eventFilter(watched, event)