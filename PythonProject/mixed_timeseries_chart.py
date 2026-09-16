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
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget


@dataclass(frozen=True)
class TimePoint:
    time: datetime
    value: float


class MixedTimeSeriesChart(QWidget):
    """
    Кастомный график через QPainter.

    Соответствие series:
        area_data   -> Cost          — жёлтая area-заливка
        bar_data    -> CPA           — синие bars
        spline_data -> ROI Confirmed — зелёная spline
        line_data   -> Covertions    — фиолетовая line

    Каждая точка входных данных:
        (datetime, float)

    У всех четырёх последовательностей должны совпадать:
    - количество точек;
    - timestamps.
    """

    COST_COLOR = QColor("#F7E98B")
    COST_BORDER_COLOR = QColor("#E4D675")

    CPA_COLOR = QColor("#326BE5")
    CPA_BORDER_COLOR = QColor("#2457C2")

    ROI_COLOR = QColor("#238D2B")
    CONVERSIONS_COLOR = QColor("#9D00D8")

    BACKGROUND_COLOR = QColor("#F9DFE4")
    PLOT_BACKGROUND_COLOR = QColor("#F7E2E5")
    PLOT_BORDER_COLOR = QColor("#B8B8B8")

    SIDEBAR_BACKGROUND_COLOR = QColor("#F7DDE2")
    SIDEBAR_TITLE_BACKGROUND = QColor("#FFFFFF")
    SIDEBAR_CELL_WHITE = QColor("#FAFAFA")
    SIDEBAR_CELL_PINK = QColor("#F7E5E8")
    SIDEBAR_TEXT_COLOR = QColor("#6A6A6A")
    SIDEBAR_TITLE_COLOR = QColor("#212121")
    SIDEBAR_SEPARATOR_COLOR = QColor("#E9E4E5")

    TOOLTIP_BACKGROUND_COLOR = QColor("#FFFFFF")
    TOOLTIP_BORDER_COLOR = QColor("#BDBDBD")
    TOOLTIP_TEXT_COLOR = QColor("#303030")
    TOOLTIP_SHADOW_COLOR = QColor(0, 0, 0, 55)

    EDIT_BUTTON_BACKGROUND = QColor("#FFFFFF")
    EDIT_BUTTON_BORDER = QColor("#E2E2E2")
    EDIT_BUTTON_ICON_COLOR = QColor("#5E5E5E")
    EDIT_BUTTON_ARROW_COLOR = QColor("#666666")

    HOVER_HALO_ALPHA = 80

    ROI_HOVER_HALO_RADIUS = 12.0
    CONVERSIONS_HOVER_HALO_RADIUS = 15.0

    HOVER_WHITE_CIRCLE_RADIUS = 6.0
    HOVER_WHITE_CIRCLE_BORDER_WIDTH = 1.2

    ROI_INNER_DIAMOND_RADIUS = 3.4
    CONVERSIONS_INNER_SQUARE_SIZE = 5.2

    AREA_HOVER_RADIUS = 4.0
    AREA_HOVER_BORDER_WIDTH = 1.5

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
        self.setMinimumSize(760, 420)

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
        self._edit_button_rect = QRectF()

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

        expected_timestamps = [point.time for point in self.area_data]

        for sequence in sequences[1:]:
            timestamps = [point.time for point in sequence]

            if timestamps != expected_timestamps:
                raise ValueError(
                    "Timestamps всех четырёх последовательностей "
                    "должны совпадать."
                )

    def set_data(
        self,
        area_data: Sequence[TimePoint | tuple[datetime, float]],
        spline_data: Sequence[TimePoint | tuple[datetime, float]],
        line_data: Sequence[TimePoint | tuple[datetime, float]],
        bar_data: Sequence[TimePoint | tuple[datetime, float]],
    ) -> None:
        """Заменяет данные и выполняет перерисовку графика."""
        self.area_data = self._normalize(area_data)
        self.spline_data = self._normalize(spline_data)
        self.line_data = self._normalize(line_data)
        self.bar_data = self._normalize(bar_data)

        self._validate()

        self._hover_index = -1
        self.update()

    def _sidebar_rect(self) -> QRectF:
        return QRectF(
            0.0,
            0.0,
            74.0,
            float(self.height()),
        )

    def _plot_area(self) -> QRectF:
        left = 112.0
        top = 95.0
        right = 98.0
        bottom = 112.0

        width = max(10.0, float(self.width()) - left - right)
        height = max(10.0, float(self.height()) - top - bottom)

        return QRectF(left, top, width, height)

    def _x_data_rect(self) -> QRectF:
        horizontal_padding = 58.0

        return QRectF(
            self._plot_rect.left() + horizontal_padding,
            self._plot_rect.top(),
            max(
                1.0,
                self._plot_rect.width() - horizontal_padding * 2.0,
            ),
            self._plot_rect.height(),
        )

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

        padding = (high - low) * 0.10

        return (
            low - padding * 0.06,
            high + padding,
        )

    def _x(self, index: int) -> float:
        data_rect = self._x_data_rect()
        count = len(self.area_data)

        if count <= 1:
            return data_rect.center().x()

        return (
            data_rect.left()
            + data_rect.width() * index / float(count - 1)
        )

    def _y(self, value: float, low: float, high: float) -> float:
        if high <= low:
            return self._plot_rect.center().y()

        ratio = (value - low) / (high - low)

        return self._plot_rect.bottom() - ratio * self._plot_rect.height()

    def _points(
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

            area_points = self._points(self.area_data, low, high)
            spline_points = self._points(self.spline_data, low, high)
            line_points = self._points(self.line_data, low, high)
            bar_points = self._points(self.bar_data, low, high)

            self._draw_sidebar(painter)
            self._draw_plot_background(painter)

            self._draw_cost_area(painter, area_points)
            self._draw_cpa_bars(painter, bar_points, low, high)
            self._draw_roi_spline(painter, spline_points)
            self._draw_conversions_line(painter, line_points)

            self._draw_edit_button(painter)

            if self._hover_index >= 0:
                self._draw_area_hover_marker(painter, area_points)

                self._draw_spline_hover_marker(
                    painter,
                    spline_points[self._hover_index],
                )

                self._draw_line_hover_marker(
                    painter,
                    line_points[self._hover_index],
                )

                self._draw_tooltip(painter)

        finally:
            painter.end()

    def _draw_sidebar(self, painter: QPainter) -> None:
        """
        Левая summary-панель, как на референсе.

        Фоны карточек чередуются:
        белый -> розовый -> белый -> розовый.
        """
        painter.save()

        sidebar = self._sidebar_rect()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.SIDEBAR_BACKGROUND_COLOR))
        painter.drawRect(sidebar)

        x = sidebar.left()
        width = sidebar.width()

        start_y = 95.0
        title_height = 58.0
        cell_height = 46.0

        title_rect = QRectF(x, start_y, width, title_height)

        painter.setBrush(QBrush(self.SIDEBAR_TITLE_BACKGROUND))
        painter.drawRect(title_rect)

        title_font = QFont("Arial", 18)
        title_font.setBold(True)

        painter.setPen(QPen(self.SIDEBAR_TITLE_COLOR))
        painter.setFont(title_font)

        painter.drawText(
            title_rect.adjusted(7.0, 0.0, -7.0, 0.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Tdy",
        )

        values = ["0%", "$0", "$0", "0", "0", "—"]

        value_font = QFont("Arial", 16)
        painter.setFont(value_font)

        current_y = start_y + title_height

        for index, value in enumerate(values):
            cell_rect = QRectF(
                x,
                current_y,
                width,
                cell_height,
            )

            background = (
                self.SIDEBAR_CELL_WHITE
                if index % 2 == 0
                else self.SIDEBAR_CELL_PINK
            )

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(background))
            painter.drawRect(cell_rect)

            painter.setPen(QPen(self.SIDEBAR_SEPARATOR_COLOR, 1))
            painter.drawLine(
                QPointF(cell_rect.left(), cell_rect.top()),
                QPointF(cell_rect.right(), cell_rect.top()),
            )

            painter.setPen(QPen(self.SIDEBAR_TEXT_COLOR))
            painter.drawText(
                cell_rect.adjusted(5.0, 0.0, -10.0, 0.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                value,
            )

            current_y += cell_height

        painter.restore()

    def _draw_plot_background(self, painter: QPainter) -> None:
        painter.save()

        painter.setPen(QPen(self.PLOT_BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.PLOT_BACKGROUND_COLOR))
        painter.drawRect(self._plot_rect)

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

        painter.setPen(QPen(self.COST_BORDER_COLOR, 1.4))
        painter.setBrush(QBrush(QColor(247, 233, 139, 115)))
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

        if len(points) > 1:
            spacing = self._x_data_rect().width() / float(len(points) - 1)
            bar_width = min(18.0, max(5.0, spacing * 0.22))
        else:
            bar_width = 14.0

        baseline_y = self._y(0.0, low, high)

        painter.setPen(QPen(self.CPA_BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.CPA_COLOR))

        bars: list[QRectF] = []

        for point in points:
            top = min(point.y(), baseline_y)
            height = max(1.0, abs(point.y() - baseline_y))

            bar_rect = QRectF(
                point.x() - bar_width / 2.0,
                top,
                bar_width,
                height,
            )

            painter.drawRoundedRect(bar_rect, 2.0, 2.0)
            bars.append(bar_rect)

        highlight_pen = QPen(QColor(255, 255, 255, 180), 1.2)
        highlight_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(highlight_pen)

        for bar_rect in bars:
            if bar_rect.height() < 3.0:
                continue

            highlight_y = bar_rect.top() + 1.7

            painter.drawLine(
                QPointF(bar_rect.left() + 2.0, highlight_y),
                QPointF(bar_rect.right() - 2.0, highlight_y),
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

            path.cubicTo(
                control_1,
                control_2,
                next_point,
            )

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

    def _draw_edit_button(self, painter: QPainter) -> None:
        """
        Декоративная edit-кнопка как на референсе:

        - белая закруглённая панель;
        - карандаш слева;
        - маленькая стрелка вниз справа;
        - нажатие ни на что не влияет.
        """
        button_width = 76.0
        button_height = 58.0
        margin_top = 20.0
        margin_right = 18.0

        self._edit_button_rect = QRectF(
            self.width() - margin_right - button_width,
            margin_top,
            button_width,
            button_height,
        )

        painter.save()

        painter.setPen(QPen(self.EDIT_BUTTON_BORDER, 1))
        painter.setBrush(QBrush(self.EDIT_BUTTON_BACKGROUND))

        painter.drawRoundedRect(
            self._edit_button_rect,
            8.0,
            8.0,
        )

        left = self._edit_button_rect.left()
        top = self._edit_button_rect.top()

        pencil_start = QPointF(left + 28.0, top + 35.0)
        pencil_end = QPointF(left + 43.0, top + 20.0)

        pencil_pen = QPen(self.EDIT_BUTTON_ICON_COLOR, 3.0)
        pencil_pen.setCapStyle(Qt.PenCapStyle.SquareCap)

        painter.setPen(pencil_pen)
        painter.drawLine(pencil_start, pencil_end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.EDIT_BUTTON_ICON_COLOR))

        pencil_tip = QPolygonF(
            [
                QPointF(left + 24.5, top + 38.5),
                QPointF(left + 29.7, top + 34.4),
                QPointF(left + 28.6, top + 39.4),
            ]
        )

        painter.drawPolygon(pencil_tip)

        painter.setPen(QPen(self.EDIT_BUTTON_ICON_COLOR, 2.2))
        painter.drawLine(
            QPointF(left + 41.7, top + 17.0),
            QPointF(left + 46.2, top + 21.5),
        )

        arrow_center_x = left + 60.0
        arrow_center_y = top + 29.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.EDIT_BUTTON_ARROW_COLOR))

        arrow = QPolygonF(
            [
                QPointF(arrow_center_x - 4.0, arrow_center_y - 2.0),
                QPointF(arrow_center_x + 4.0, arrow_center_y - 2.0),
                QPointF(arrow_center_x, arrow_center_y + 3.0),
            ]
        )

        painter.drawPolygon(arrow)

        painter.restore()

    def _draw_area_hover_marker(
        self,
        painter: QPainter,
        points: list[QPointF],
    ) -> None:
        if (
            self._hover_index < 0
            or self._hover_index >= len(points)
        ):
            return

        painter.save()

        painter.setPen(QPen(self.COST_BORDER_COLOR, 1.5))
        painter.setBrush(QBrush(QColor("#FFFFFF")))

        painter.drawEllipse(
            points[self._hover_index],
            self.AREA_HOVER_RADIUS,
            self.AREA_HOVER_RADIUS,
        )

        painter.restore()

    def _draw_hover_halo(
        self,
        painter: QPainter,
        center: QPointF,
        color: QColor,
        radius: float,
    ) -> None:
        painter.save()

        halo_color = QColor(
            color.red(),
            color.green(),
            color.blue(),
            self.HOVER_HALO_ALPHA,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo_color))

        painter.drawEllipse(center, radius, radius)

        painter.restore()

    def _draw_spline_hover_marker(
        self,
        painter: QPainter,
        center: QPointF,
    ) -> None:
        """
        ROI Confirmed:
        зелёный halo -> белый круг -> зелёный ромб.
        """
        self._draw_hover_halo(
            painter,
            center,
            self.ROI_COLOR,
            self.ROI_HOVER_HALO_RADIUS,
        )

        painter.save()

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                self.HOVER_WHITE_CIRCLE_BORDER_WIDTH,
            )
        )
        painter.setBrush(QBrush(QColor("#FFFFFF")))

        painter.drawEllipse(
            center,
            self.HOVER_WHITE_CIRCLE_RADIUS,
            self.HOVER_WHITE_CIRCLE_RADIUS,
        )

        radius = self.ROI_INNER_DIAMOND_RADIUS

        diamond = QPolygonF(
            [
                QPointF(center.x(), center.y() - radius),
                QPointF(center.x() + radius, center.y()),
                QPointF(center.x(), center.y() + radius),
                QPointF(center.x() - radius, center.y()),
            ]
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.ROI_COLOR))
        painter.drawPolygon(diamond)

        painter.restore()

    def _draw_line_hover_marker(
        self,
        painter: QPainter,
        center: QPointF,
    ) -> None:
        """
        Covertions:
        увеличенный фиолетовый halo -> белый круг -> компактный квадрат.
        """
        self._draw_hover_halo(
            painter,
            center,
            self.CONVERSIONS_COLOR,
            self.CONVERSIONS_HOVER_HALO_RADIUS,
        )

        painter.save()

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                self.HOVER_WHITE_CIRCLE_BORDER_WIDTH,
            )
        )
        painter.setBrush(QBrush(QColor("#FFFFFF")))

        painter.drawEllipse(
            center,
            self.HOVER_WHITE_CIRCLE_RADIUS,
            self.HOVER_WHITE_CIRCLE_RADIUS,
        )

        size = self.CONVERSIONS_INNER_SQUARE_SIZE

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.CONVERSIONS_COLOR))

        painter.drawRect(
            QRectF(
                center.x() - size / 2.0,
                center.y() - size / 2.0,
                size,
                size,
            )
        )

        painter.restore()

    def _tooltip_rect(self) -> QRectF:
        tooltip_width = 320.0
        tooltip_height = 154.0

        current_x = self._x(self._hover_index)

        x = current_x + 18.0
        y = self._plot_rect.top() + 12.0

        if x + tooltip_width > self.width() - 8.0:
            x = current_x - tooltip_width - 18.0

        x = max(8.0, x)
        y = max(8.0, y)

        if y + tooltip_height > self.height() - 8.0:
            y = self.height() - tooltip_height - 8.0

        return QRectF(x, y, tooltip_width, tooltip_height)

    def _draw_tooltip(self, painter: QPainter) -> None:
        if self._hover_index < 0:
            return

        cost = self.area_data[self._hover_index]
        cpa = self.bar_data[self._hover_index]
        roi = self.spline_data[self._hover_index]
        conversions = self.line_data[self._hover_index]

        tooltip_rect = self._tooltip_rect()

        painter.save()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.TOOLTIP_SHADOW_COLOR))

        painter.drawRoundedRect(
            tooltip_rect.translated(3.0, 4.0),
            7.0,
            7.0,
        )

        painter.setPen(QPen(self.TOOLTIP_BORDER_COLOR, 1))
        painter.setBrush(QBrush(self.TOOLTIP_BACKGROUND_COLOR))

        painter.drawRoundedRect(
            tooltip_rect,
            7.0,
            7.0,
        )

        text_x = tooltip_rect.left() + 16.0
        y = tooltip_rect.top() + 29.0

        painter.setFont(QFont("Arial", 16))
        painter.setPen(QPen(self.TOOLTIP_TEXT_COLOR))

        painter.drawText(
            QPointF(text_x, y),
            cost.time.strftime("%d.%m.%Y"),
        )

        y += 29.0

        self._draw_tooltip_row(
            painter,
            text_x,
            y,
            self.COST_COLOR,
            "Cost:",
            cost.value,
            integer=False,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter,
            text_x,
            y,
            self.CPA_COLOR,
            "CPA:",
            cpa.value,
            integer=False,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter,
            text_x,
            y,
            self.ROI_COLOR,
            "ROI Confirmed:",
            roi.value,
            integer=False,
        )

        y += 27.0

        self._draw_tooltip_row(
            painter,
            text_x,
            y,
            self.CONVERSIONS_COLOR,
            "Covertions:",
            conversions.value,
            integer=True,
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
        integer: bool,
    ) -> None:
        dot_radius = 7.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))

        painter.drawEllipse(
            QPointF(
                x + dot_radius,
                y - dot_radius + 1.0,
            ),
            dot_radius,
            dot_radius,
        )

        label_font = QFont("Arial", 16)

        painter.setFont(label_font)
        painter.setPen(QPen(QColor("#303030")))

        label_x = x + 24.0
        label_text = f"{label} "

        painter.drawText(
            QPointF(label_x, y + 5.0),
            label_text,
        )

        metrics = QFontMetrics(label_font)
        value_x = label_x + metrics.horizontalAdvance(label_text)

        value_font = QFont("Arial", 16)
        value_font.setBold(True)

        painter.setFont(value_font)

        text_value = (
            str(int(round(value)))
            if integer
            else f"{value:.2f}"
        )

        painter.drawText(
            QPointF(value_x, y + 5.0),
            text_value,
        )

    def mouseMoveEvent(self, event) -> None:
        position = event.position()

        if not self._plot_rect.contains(position):
            if self._hover_index != -1:
                self._hover_index = -1
                self.update()

            return

        point_count = len(self.area_data)

        if point_count == 1:
            index = 0
        else:
            data_rect = self._x_data_rect()

            fraction = (
                (position.x() - data_rect.left())
                / data_rect.width()
            )

            index = int(round(fraction * (point_count - 1)))
            index = max(0, min(index, point_count - 1))

        if index != self._hover_index:
            self._hover_index = index
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hover_index != -1:
            self._hover_index = -1
            self.update()

        super().leaveEvent(event)