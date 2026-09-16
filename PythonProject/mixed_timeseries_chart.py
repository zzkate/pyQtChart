from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from PySide6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QBrush,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class TimePoint:
    time: datetime
    value: float


class ChartTooltip(QFrame):
    """Всплывающая карточка с показателями для одной даты."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("chartTooltip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.date_label = QLabel(self)
        self.date_label.setObjectName("tooltipDate")

        self.area_label = QLabel(self)
        self.spline_label = QLabel(self)
        self.line_label = QLabel(self)
        self.bar_label = QLabel(self)

        for label in (
            self.area_label,
            self.spline_label,
            self.line_label,
            self.bar_label,
        ):
            label.setObjectName("tooltipText")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)

        layout.addWidget(self.date_label)
        layout.addWidget(self.area_label)
        layout.addWidget(self.spline_label)
        layout.addWidget(self.line_label)
        layout.addWidget(self.bar_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(3, 4)
        shadow.setColor(QColor(0, 0, 0, 85))
        self.setGraphicsEffect(shadow)

        self.hide()

    def set_values(
        self,
        timestamp: datetime,
        area_value: float,
        spline_value: float,
        line_value: float,
        bar_value: float,
    ) -> None:
        self.date_label.setText(timestamp.strftime("%d.%m.%Y"))

        self.area_label.setText(
            f'<span style="color:#F7E98B; font-size:21px;">●</span> '
            f'Area: <b>{area_value:.2f}</b>'
        )
        self.spline_label.setText(
            f'<span style="color:#238D2B; font-size:21px;">●</span> '
            f'Spline: <b>{spline_value:.2f}</b>'
        )
        self.line_label.setText(
            f'<span style="color:#9D00D8; font-size:21px;">●</span> '
            f'Line: <b>{line_value:.2f}</b>'
        )
        self.bar_label.setText(
            f'<span style="color:#326BE5; font-size:21px;">●</span> '
            f'Bar: <b>{bar_value:.2f}</b>'
        )

        self.adjustSize()


class MixedTimeSeriesChart(QWidget):
    """
    Кастомный график, рисуемый через QPainter.

    Принимает четыре time-series одинаковой длины и с идентичными timestamps:

    area_data:
        жёлтая полупрозрачная area-заливка.

    spline_data:
        зелёная сглаженная кривая.

    line_data:
        фиолетовая ломаная с маркерами.

    bar_data:
        синие вертикальные бары.

    Формат данных:

        [
            (datetime(2026, 6, 10), 44.36),
            (datetime(2026, 6, 11), 38.10),
        ]
    """

    AREA_COLOR = QColor("#F7E98B")
    SPLINE_COLOR = QColor("#238D2B")
    LINE_COLOR = QColor("#9D00D8")
    BAR_COLOR = QColor("#326BE5")

    PLOT_BACKGROUND = QColor("#F7E2E5")
    GRID_COLOR = QColor("#D5C8CB")
    AXIS_COLOR = QColor("#A7A1A2")
    LABEL_COLOR = QColor("#555555")

    def __init__(
        self,
        area_data: Sequence[TimePoint | tuple[datetime, float]],
        spline_data: Sequence[TimePoint | tuple[datetime, float]],
        line_data: Sequence[TimePoint | tuple[datetime, float]],
        bar_data: Sequence[TimePoint | tuple[datetime, float]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("chartContainer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.area_data = self._normalize_data(area_data)
        self.spline_data = self._normalize_data(spline_data)
        self.line_data = self._normalize_data(line_data)
        self.bar_data = self._normalize_data(bar_data)

        self._validate_data()

        self.hover_index: int | None = None
        self._plot_rect = QRectF()

        self.tooltip = ChartTooltip(self)
        self.tooltip.hide()

    @staticmethod
    def _normalize_data(
        data: Sequence[TimePoint | tuple[datetime, float]],
    ) -> list[TimePoint]:
        normalized: list[TimePoint] = []

        for point in data:
            if isinstance(point, TimePoint):
                normalized.append(point)
            else:
                timestamp, value = point
                normalized.append(TimePoint(timestamp, float(value)))

        return sorted(normalized, key=lambda item: item.time)

    def _validate_data(self) -> None:
        all_series = (
            self.area_data,
            self.spline_data,
            self.line_data,
            self.bar_data,
        )

        if not all(all_series):
            raise ValueError("Все четыре time-series должны содержать данные.")

        lengths = {len(series) for series in all_series}

        if len(lengths) != 1:
            raise ValueError(
                "Все time-series должны иметь одинаковое количество точек."
            )

        expected_times = [point.time for point in self.area_data]

        for series in all_series[1:]:
            current_times = [point.time for point in series]

            if current_times != expected_times:
                raise ValueError(
                    "Timestamps всех четырёх time-series должны совпадать."
                )

    def set_data(
        self,
        area_data: Sequence[TimePoint | tuple[datetime, float]],
        spline_data: Sequence[TimePoint | tuple[datetime, float]],
        line_data: Sequence[TimePoint | tuple[datetime, float]],
        bar_data: Sequence[TimePoint | tuple[datetime, float]],
    ) -> None:
        """Заменяет данные и запрашивает перерисовку графика."""
        self.area_data = self._normalize_data(area_data)
        self.spline_data = self._normalize_data(spline_data)
        self.line_data = self._normalize_data(line_data)
        self.bar_data = self._normalize_data(bar_data)

        self._validate_data()

        self.hover_index = None
        self.tooltip.hide()
        self.update()

    def _value_range(self) -> tuple[float, float]:
        values = [
            point.value
            for series in (
                self.area_data,
                self.spline_data,
                self.line_data,
                self.bar_data,
            )
            for point in series
        ]

        minimum = min(0.0, min(values))
        maximum = max(values)

        if maximum == minimum:
            maximum += 1.0

        padding = (maximum - minimum) * 0.12

        return minimum - padding * 0.20, maximum + padding

    def _make_plot_rect(self) -> QRectF:
        """
        Внутреннее поле графика.

        Слева оставляется место для Y-подписей,
        снизу — для дат по оси X.
        """
        left = 68
        top = 28
        right = 30
        bottom = 54

        return QRectF(
            left,
            top,
            max(1, self.width() - left - right),
            max(1, self.height() - top - bottom),
        )

    def _x_for_index(self, index: int, rect: QRectF) -> float:
        count = len(self.area_data)

        if count <= 1:
            return rect.center().x()

        return rect.left() + rect.width() * index / (count - 1)

    @staticmethod
    def _y_for_value(
        value: float,
        minimum: float,
        maximum: float,
        rect: QRectF,
    ) -> float:
        ratio = (value - minimum) / (maximum - minimum)
        return rect.bottom() - ratio * rect.height()

    def _points_for_series(
        self,
        data: Sequence[TimePoint],
        rect: QRectF,
        minimum: float,
        maximum: float,
    ) -> list[QPointF]:
        return [
            QPointF(
                self._x_for_index(index, rect),
                self._y_for_value(point.value, minimum, maximum, rect),
            )
            for index, point in enumerate(data)
        ]

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self._plot_rect = self._make_plot_rect()
        minimum, maximum = self._value_range()

        self._draw_plot_background(painter, self._plot_rect)
        self._draw_grid_and_y_axis(
            painter,
            self._plot_rect,
            minimum,
            maximum,
        )
        self._draw_x_labels(painter, self._plot_rect)

        area_points = self._points_for_series(
            self.area_data,
            self._plot_rect,
            minimum,
            maximum,
        )
        spline_points = self._points_for_series(
            self.spline_data,
            self._plot_rect,
            minimum,
            maximum,
        )
        line_points = self._points_for_series(
            self.line_data,
            self._plot_rect,
            minimum,
            maximum,
        )
        bar_points = self._points_for_series(
            self.bar_data,
            self._plot_rect,
            minimum,
            maximum,
        )

        self._draw_area(painter, area_points, self._plot_rect)
        self._draw_bars(
            painter,
            bar_points,
            self._plot_rect,
            minimum,
            maximum,
        )
        self._draw_spline(painter, spline_points)
        self._draw_line(painter, line_points)

        if self.hover_index is not None:
            self._draw_hover_indicator(
                painter,
                self.hover_index,
                self._plot_rect,
            )

    def _draw_plot_background(
        self,
        painter: QPainter,
        rect: QRectF,
    ) -> None:
        painter.save()

        painter.setPen(QPen(QColor("#B8B8B8"), 1))
        painter.setBrush(QBrush(self.PLOT_BACKGROUND))
        painter.drawRect(rect)

        painter.restore()

    def _draw_grid_and_y_axis(
        self,
        painter: QPainter,
        rect: QRectF,
        minimum: float,
        maximum: float,
    ) -> None:
        painter.save()

        tick_count = 6
        font = QFont("Arial", 10)
        painter.setFont(font)

        grid_pen = QPen(self.GRID_COLOR, 1)
        grid_pen.setStyle(Qt.DotLine)

        axis_pen = QPen(self.AXIS_COLOR, 1)
        label_pen = QPen(self.LABEL_COLOR)

        for index in range(tick_count):
            ratio = index / (tick_count - 1)
            y = rect.bottom() - ratio * rect.height()
            value = minimum + ratio * (maximum - minimum)

            painter.setPen(grid_pen)
            painter.drawLine(
                QPointF(rect.left(), y),
                QPointF(rect.right(), y),
            )

            painter.setPen(label_pen)

            text_rect = QRectF(
                4,
                y - 12,
                rect.left() - 12,
                24,
            )

            painter.drawText(
                text_rect,
                Qt.AlignRight | Qt.AlignVCenter,
                f"{value:.0f}",
            )

        painter.setPen(axis_pen)
        painter.drawLine(
            QPointF(rect.left(), rect.top()),
            QPointF(rect.left(), rect.bottom()),
        )
        painter.drawLine(
            QPointF(rect.left(), rect.bottom()),
            QPointF(rect.right(), rect.bottom()),
        )

        painter.restore()

    def _draw_x_labels(
        self,
        painter: QPainter,
        rect: QRectF,
    ) -> None:
        painter.save()

        painter.setPen(QPen(self.LABEL_COLOR))
        painter.setFont(QFont("Arial", 10))

        count = len(self.area_data)

        if count <= 8:
            indexes = list(range(count))
        else:
            step = max(1, count // 7)
            indexes = list(range(0, count, step))

            if indexes[-1] != count - 1:
                indexes.append(count - 1)

        for index in indexes:
            x = self._x_for_index(index, rect)

            label_rect = QRectF(
                x - 34,
                rect.bottom() + 8,
                68,
                24,
            )

            painter.drawText(
                label_rect,
                Qt.AlignCenter,
                self.area_data[index].time.strftime("%d.%m"),
            )

        painter.restore()

    def _draw_area(
        self,
        painter: QPainter,
        points: list[QPointF],
        rect: QRectF,
    ) -> None:
        if not points:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        path.lineTo(QPointF(points[-1].x(), rect.bottom()))
        path.lineTo(QPointF(points[0].x(), rect.bottom()))
        path.closeSubpath()

        painter.setPen(QPen(self.AREA_COLOR.darker(112), 1.5))
        painter.setBrush(QBrush(QColor(247, 233, 139, 125)))
        painter.drawPath(path)

        painter.restore()

    def _draw_spline(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if len(points) < 2:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        if len(points) == 2:
            path.lineTo(points[1])
        else:
            for index in range(len(points) - 1):
                current = points[index]
                next_point = points[index + 1]

                control_1 = QPointF(
                    current.x() + (next_point.x() - current.x()) * 0.45,
                    current.y(),
                )
                control_2 = QPointF(
                    current.x() + (next_point.x() - current.x()) * 0.55,
                    next_point.y(),
                )

                path.cubicTo(control_1, control_2, next_point)

        pen = QPen(self.SPLINE_COLOR, 2.4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.restore()

    def _draw_line(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if not points:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        pen = QPen(self.LINE_COLOR, 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setPen(QPen(self.LINE_COLOR, 1))
        painter.setBrush(QBrush(self.LINE_COLOR))

        marker_size = 7.5

        for point in points:
            painter.drawRect(
                QRectF(
                    point.x() - marker_size / 2,
                    point.y() - marker_size / 2,
                    marker_size,
                    marker_size,
                )
            )

        painter.restore()

    def _draw_bars(
        self,
        painter: QPainter,
        points: list[QPointF],
        rect: QRectF,
        minimum: float,
        maximum: float,
    ) -> None:
        if not points:
            return

        painter.save()

        count = len(points)

        if count > 1:
            spacing = rect.width() / (count - 1)
            bar_width = max(4.0, min(16.0, spacing * 0.28))
        else:
            bar_width = 14.0

        baseline_y = self._y_for_value(
            0.0,
            minimum,
            maximum,
            rect,
        )

        painter.setPen(QPen(self.BAR_COLOR.darker(110), 1))
        painter.setBrush(QBrush(self.BAR_COLOR))

        for point in points:
            top = min(point.y(), baseline_y)
            height = abs(baseline_y - point.y())

            painter.drawRoundedRect(
                QRectF(
                    point.x() - bar_width / 2,
                    top,
                    bar_width,
                    max(height, 1.0),
                ),
                2.0,
                2.0,
            )

        painter.restore()

    def _draw_hover_indicator(
        self,
        painter: QPainter,
        index: int,
        rect: QRectF,
    ) -> None:
        painter.save()

        x = self._x_for_index(index, rect)

        guide_pen = QPen(QColor(70, 70, 70, 90), 1)
        guide_pen.setStyle(Qt.DashLine)

        painter.setPen(guide_pen)
        painter.drawLine(
            QPointF(x, rect.top()),
            QPointF(x, rect.bottom()),
        )

        painter.restore()

    def mouseMoveEvent(self, event) -> None:
        if not self._plot_rect.contains(event.position()):
            self.hover_index = None
            self.tooltip.hide()
            self.update()
            return

        count = len(self.area_data)

        if count == 1:
            nearest_index = 0
        else:
            relative_x = event.position().x() - self._plot_rect.left()
            fraction = relative_x / self._plot_rect.width()

            nearest_index = int(round(fraction * (count - 1)))
            nearest_index = max(0, min(nearest_index, count - 1))

        if self.hover_index != nearest_index:
            self.hover_index = nearest_index
            self._show_tooltip(nearest_index)
            self.update()

    def leaveEvent(self, event) -> None:
        self.hover_index = None
        self.tooltip.hide()
        self.update()
        super().leaveEvent(event)

    def _show_tooltip(self, index: int) -> None:
        area_point = self.area_data[index]
        spline_point = self.spline_data[index]
        line_point = self.line_data[index]
        bar_point = self.bar_data[index]

        self.tooltip.set_values(
            timestamp=area_point.time,
            area_value=area_point.value,
            spline_value=spline_point.value,
            line_value=line_point.value,
            bar_value=bar_point.value,
        )

        x = int(self._x_for_index(index, self._plot_rect) + 16)
        y = int(self._plot_rect.top() + 12)

        x = max(8, x)
        y = max(8, y)

        x = min(
            x,
            self.width() - self.tooltip.width() - 8,
        )

        self.tooltip.move(x, y)
        self.tooltip.show()
        self.tooltip.raise_()