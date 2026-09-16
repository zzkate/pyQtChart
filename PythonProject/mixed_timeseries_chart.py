from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QColor,
    QBrush,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget


@dataclass(frozen=True)
class TimePoint:
    time: datetime
    value: float


class MixedTimeSeriesChart(QWidget):
    """
    Кастомный QPainter-график.

    Входные series:
        area_data   -> Cost          (жёлтая area-заливка)
        bar_data    -> CPA           (синие столбцы)
        spline_data -> ROI Confirmed (зелёная сглаженная линия)
        line_data   -> Covertions    (фиолетовая линия)

    Каждый элемент:
        (datetime, float)

    У всех 4 наборов должно быть одинаковое число точек
    и одинаковые timestamps.
    """

    COST_COLOR = QColor("#F7E98B")
    CPA_COLOR = QColor("#326BE5")
    ROI_COLOR = QColor("#238D2B")
    CONVERSIONS_COLOR = QColor("#9D00D8")

    BACKGROUND_COLOR = QColor("#F9DFE4")
    PLOT_BACKGROUND_COLOR = QColor("#F7E2E5")
    PLOT_BORDER_COLOR = QColor("#B8B8B8")

    Y_LABEL_BACKGROUND_COLOR = QColor("#FAFAFA")
    Y_LABEL_TEXT_COLOR = QColor("#4A4A4A")

    TOOLTIP_BACKGROUND_COLOR = QColor("#FFFFFF")
    TOOLTIP_BORDER_COLOR = QColor("#BDBDBD")
    TOOLTIP_TEXT_COLOR = QColor("#303030")
    TOOLTIP_SHADOW_COLOR = QColor(0, 0, 0, 55)

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
        self.setMinimumSize(700, 400)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMouseTracking(True)

        self.area_data = self._normalize(area_data)
        self.spline_data = self._normalize(spline_data)
        self.line_data = self._normalize(line_data)
        self.bar_data = self._normalize(bar_data)

        self._validate()

        self._plot_rect = QRectF()
        self._hover_index = -1

    @staticmethod
    def _normalize(
        values: Sequence[TimePoint | tuple[datetime, float]],
    ) -> list[TimePoint]:
        result: list[TimePoint] = []

        for item in values:
            if isinstance(item, TimePoint):
                result.append(item)
            else:
                timestamp, value = item
                result.append(TimePoint(timestamp, float(value)))

        return sorted(result, key=lambda point: point.time)

    def _validate(self) -> None:
        sequences = (
            self.area_data,
            self.spline_data,
            self.line_data,
            self.bar_data,
        )

        if not all(sequences):
            raise ValueError(
                "Все четыре последовательности должны содержать данные."
            )

        lengths = {len(sequence) for sequence in sequences}

        if len(lengths) != 1:
            raise ValueError(
                "Все последовательности должны иметь одинаковую длину."
            )

        timestamps = [point.time for point in self.area_data]

        for sequence in sequences[1:]:
            current_timestamps = [point.time for point in sequence]

            if current_timestamps != timestamps:
                raise ValueError(
                    "Временные метки во всех последовательностях "
                    "должны совпадать."
                )

    def set_data(
        self,
        area_data: Sequence[TimePoint | tuple[datetime, float]],
        spline_data: Sequence[TimePoint | tuple[datetime, float]],
        line_data: Sequence[TimePoint | tuple[datetime, float]],
        bar_data: Sequence[TimePoint | tuple[datetime, float]],
    ) -> None:
        """Заменяет данные и запускает перерисовку."""
        self.area_data = self._normalize(area_data)
        self.spline_data = self._normalize(spline_data)
        self.line_data = self._normalize(line_data)
        self.bar_data = self._normalize(bar_data)

        self._validate()

        self._hover_index = -1
        self.update()

    def _plot_area(self) -> QRectF:
        left = 78.0
        top = 28.0
        right = 28.0
        bottom = 28.0

        width = max(10.0, float(self.width()) - left - right)
        height = max(10.0, float(self.height()) - top - bottom)

        return QRectF(left, top, width, height)

    def _range_y(self) -> tuple[float, float]:
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

        low = min(0.0, min(values))
        high = max(values)

        if high <= low:
            high = low + 1.0

        padding = (high - low) * 0.12

        return (
            low - padding * 0.05,
            high + padding,
        )

    def _x(self, index: int) -> float:
        count = len(self.area_data)

        if count <= 1:
            return self._plot_rect.center().x()

        return (
            self._plot_rect.left()
            + self._plot_rect.width() * index / float(count - 1)
        )

    def _y(self, value: float, low: float, high: float) -> float:
        if high <= low:
            return self._plot_rect.center().y()

        ratio = (value - low) / (high - low)

        return self._plot_rect.bottom() - ratio * self._plot_rect.height()

    def _series_points(
        self,
        series: Sequence[TimePoint],
        low: float,
        high: float,
    ) -> list[QPointF]:
        return [
            QPointF(
                self._x(index),
                self._y(point.value, low, high),
            )
            for index, point in enumerate(series)
        ]

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), self.BACKGROUND_COLOR)

            self._plot_rect = self._plot_area()
            low, high = self._range_y()

            self._draw_plot_background(painter)
            self._draw_y_labels(painter, low, high)

            area_points = self._series_points(self.area_data, low, high)
            spline_points = self._series_points(self.spline_data, low, high)
            line_points = self._series_points(self.line_data, low, high)
            bar_points = self._series_points(self.bar_data, low, high)

            self._draw_cost_area(painter, area_points)
            self._draw_cpa_bars(painter, bar_points, low, high)
            self._draw_roi_spline(painter, spline_points)
            self._draw_conversions_line(painter, line_points)

            if self._hover_index >= 0:
                self._draw_hover_line(painter)
                self._draw_tooltip(painter, low, high)

        finally:
            painter.end()

    def _draw_plot_background(self, painter: QPainter) -> None:
        painter.save()

        painter.setPen(QPen(self.PLOT_BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.PLOT_BACKGROUND_COLOR))
        painter.drawRect(self._plot_rect)

        painter.restore()

    def _draw_y_labels(
        self,
        painter: QPainter,
        low: float,
        high: float,
    ) -> None:
        """
        Белые карточки Y-значений слева.
        Без X-подписей, осей и горизонтальной сетки.
        """
        painter.save()

        label_width = 58.0
        label_height = 32.0
        label_x = 4.0
        ticks = 6

        painter.setFont(QFont("Arial", 10))

        for i in range(ticks):
            ratio = i / float(ticks - 1)
            y = self._plot_rect.bottom() - ratio * self._plot_rect.height()
            value = low + ratio * (high - low)

            label_rect = QRectF(
                label_x,
                y - label_height / 2.0,
                label_width,
                label_height,
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.Y_LABEL_BACKGROUND_COLOR))
            painter.drawRect(label_rect)

            painter.setPen(QPen(self.Y_LABEL_TEXT_COLOR))
            painter.drawText(
                label_rect.adjusted(2.0, 0.0, -5.0, 0.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.0f}",
            )

        painter.restore()

    def _draw_cost_area(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if len(points) < 2:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        path.lineTo(
            QPointF(points[-1].x(), self._plot_rect.bottom())
        )
        path.lineTo(
            QPointF(points[0].x(), self._plot_rect.bottom())
        )
        path.closeSubpath()

        painter.setPen(QPen(QColor("#E4D675"), 1.5))
        painter.setBrush(QBrush(QColor(247, 233, 139, 125)))
        painter.drawPath(path)

        painter.restore()

    def _draw_cpa_bars(
        self,
        painter: QPainter,
        points: list[QPointF],
        low: float,
        high: float,
    ) -> None:
        if not points:
            return

        painter.save()

        point_count = len(points)

        if point_count > 1:
            spacing = self._plot_rect.width() / float(point_count - 1)
            bar_width = min(16.0, max(5.0, spacing * 0.22))
        else:
            bar_width = 14.0

        baseline_y = self._y(0.0, low, high)

        painter.setPen(QPen(QColor("#2457C2"), 1))
        painter.setBrush(QBrush(self.CPA_COLOR))

        for point in points:
            top = min(point.y(), baseline_y)
            height = max(1.0, abs(point.y() - baseline_y))

            painter.drawRoundedRect(
                QRectF(
                    point.x() - bar_width / 2.0,
                    top,
                    bar_width,
                    height,
                ),
                2.0,
                2.0,
            )

        painter.restore()

    def _draw_roi_spline(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if len(points) < 2:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        for index in range(len(points) - 1):
            current = points[index]
            next_point = points[index + 1]
            dx = next_point.x() - current.x()

            control_1 = QPointF(
                current.x() + dx * 0.45,
                current.y(),
            )

            control_2 = QPointF(
                current.x() + dx * 0.55,
                next_point.y(),
            )

            path.cubicTo(control_1, control_2, next_point)

        pen = QPen(self.ROI_COLOR, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(QBrush())
        painter.drawPath(path)

        painter.restore()

    def _draw_conversions_line(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if len(points) < 2:
            return

        painter.save()

        path = QPainterPath()
        path.moveTo(points[0])

        for point in points[1:]:
            path.lineTo(point)

        pen = QPen(self.CONVERSIONS_COLOR, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(QBrush())
        painter.drawPath(path)

        marker_size = 8.0

        painter.setPen(QPen(self.CONVERSIONS_COLOR, 1))
        painter.setBrush(QBrush(self.CONVERSIONS_COLOR))

        for point in points:
            painter.drawRect(
                QRectF(
                    point.x() - marker_size / 2.0,
                    point.y() - marker_size / 2.0,
                    marker_size,
                    marker_size,
                )
            )

        painter.restore()

    def _draw_hover_line(self, painter: QPainter) -> None:
        x = self._x(self._hover_index)

        painter.save()

        pen = QPen(QColor(70, 70, 70, 105), 1)
        pen.setStyle(Qt.PenStyle.DashLine)

        painter.setPen(pen)
        painter.drawLine(
            QPointF(x, self._plot_rect.top()),
            QPointF(x, self._plot_rect.bottom()),
        )

        painter.restore()

    def _tooltip_rect(self) -> QRectF:
        """
        Вычисляет положение tooltip.

        Карточка будет справа от курсора. Если справа мало места,
        она появится слева от текущей точки.
        """
        tooltip_width = 315.0
        tooltip_height = 154.0

        point_x = self._x(self._hover_index)
        point_y = self._plot_rect.top() + 12.0

        x = point_x + 16.0
        y = point_y

        if x + tooltip_width > self.width() - 8.0:
            x = point_x - tooltip_width - 16.0

        x = max(8.0, x)
        y = max(8.0, y)

        if y + tooltip_height > self.height() - 8.0:
            y = self.height() - tooltip_height - 8.0

        return QRectF(x, y, tooltip_width, tooltip_height)

    def _draw_tooltip(
        self,
        painter: QPainter,
        low: float,
        high: float,
    ) -> None:
        if self._hover_index < 0:
            return

        cost_point = self.area_data[self._hover_index]
        cpa_point = self.bar_data[self._hover_index]
        roi_point = self.spline_data[self._hover_index]
        conversions_point = self.line_data[self._hover_index]

        tooltip_rect = self._tooltip_rect()

        painter.save()

        shadow_rect = tooltip_rect.translated(3.0, 4.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.TOOLTIP_SHADOW_COLOR))
        painter.drawRoundedRect(shadow_rect, 7.0, 7.0)

        painter.setPen(QPen(self.TOOLTIP_BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.TOOLTIP_BACKGROUND_COLOR))
        painter.drawRoundedRect(tooltip_rect, 7.0, 7.0)

        left = tooltip_rect.left() + 15.0
        y = tooltip_rect.top() + 29.0

        date_font = QFont("Arial", 16)
        painter.setFont(date_font)
        painter.setPen(QPen(self.TOOLTIP_TEXT_COLOR))

        painter.drawText(
            QPointF(left, y),
            cost_point.time.strftime("%d.%m.%Y"),
        )

        y += 29.0

        self._draw_tooltip_row(
            painter=painter,
            x=left,
            y=y,
            color=self.COST_COLOR,
            label="Cost:",
            value=cost_point.value,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter=painter,
            x=left,
            y=y,
            color=self.CPA_COLOR,
            label="CPA:",
            value=cpa_point.value,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter=painter,
            x=left,
            y=y,
            color=self.ROI_COLOR,
            label="ROI Confirmed:",
            value=roi_point.value,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter=painter,
            x=left,
            y=y,
            color=self.CONVERSIONS_COLOR,
            label="Covertions:",
            value=conversions_point.value,
        )

        painter.restore()

    @staticmethod
    def _draw_tooltip_row(
        painter: QPainter,
        x: float,
        y: float,
        color: QColor,
        label: str,
        value: float,
    ) -> None:
        """Рисует цветную точку, название показателя и жирное значение."""
        dot_radius = 7.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(
            QPointF(x + dot_radius, y - dot_radius + 1.0),
            dot_radius,
            dot_radius,
        )

        label_font = QFont("Arial", 16)
        painter.setFont(label_font)
        painter.setPen(QPen(QColor("#303030")))

        text_x = x + 24.0
        painter.drawText(
            QPointF(text_x, y + 5.0),
            f"{label} ",
        )

        metrics = QFontMetrics(label_font)
        value_x = text_x + metrics.horizontalAdvance(f"{label} ")

        value_font = QFont("Arial", 16)
        value_font.setBold(True)

        painter.setFont(value_font)
        painter.drawText(
            QPointF(value_x, y + 5.0),
            f"{value:.2f}",
        )

    def mouseMoveEvent(self, event) -> None:
        mouse_position = event.position()

        if not self._plot_rect.contains(mouse_position):
            if self._hover_index != -1:
                self._hover_index = -1
                self.update()

            return

        count = len(self.area_data)

        if count == 1:
            index = 0
        else:
            fraction = (
                (mouse_position.x() - self._plot_rect.left())
                / self._plot_rect.width()
            )

            index = int(round(fraction * (count - 1)))
            index = max(0, min(index, count - 1))

        if index != self._hover_index:
            self._hover_index = index
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hover_index != -1:
            self._hover_index = -1
            self.update()

        super().leaveEvent(event)