import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMainWindow

from PySide6.QtCharts import (
    QAreaSeries,
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QSplineSeries,
)


class TimeSeriesChart(QChartView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        self.chart = QChart()
        self.chart.setTitle(
            "Area, Spline, Line and Bar"
        )
        self.chart.setAnimationOptions(
            QChart.AnimationOption.NoAnimation
        )
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(
            Qt.AlignmentFlag.AlignBottom
        )

        self.setChart(self.chart)

        # Храним ссылки на объекты.
        # Это упрощает управление временем жизни объектов
        # в PySide6.
        self.axis_x = None
        self.axis_y = None

        self.area_upper = None
        self.area_lower = None
        self.area_series = None
        self.spline_series = None
        self.line_series = None
        self.bar_set = None
        self.bar_series = None

    def plot(
        self,
        area_values,
        spline_values,
        line_values,
        bar_values,
        categories=None,
    ):
        series_data = (
            area_values,
            spline_values,
            line_values,
            bar_values,
        )

        if not all(series_data):
            raise ValueError(
                "Все последовательности должны быть непустыми"
            )

        lengths = {
            len(values)
            for values in series_data
        }

        if len(lengths) != 1:
            raise ValueError(
                "Все последовательности должны иметь "
                "одинаковую длину"
            )

        count = len(area_values)

        if categories is None:
            categories = [
                str(index)
                for index in range(count)
            ]

        if len(categories) != count:
            raise ValueError(
                "Количество категорий должно совпадать "
                "с длиной данных"
            )

        # Если метод вызван повторно, удаляем series из chart.
        # Не удаляем оси вручную и не вызываем deleteLater().
        self.chart.removeAllSeries()

        # Создаём новые оси.
        # Старые Python-ссылки заменяются после очистки chart.
        self.axis_x = QBarCategoryAxis()
        self.axis_x.setTitleText("Время")
        self.axis_x.append(categories)

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Значение")

        all_values = (
            list(area_values)
            + list(spline_values)
            + list(line_values)
            + list(bar_values)
        )

        min_value = min(all_values)
        max_value = max(all_values)

        if min_value == max_value:
            margin = max(
                abs(min_value) * 0.1,
                1.0,
            )
        else:
            margin = (
                max_value - min_value
            ) * 0.1

        self.axis_y.setRange(
            min(0.0, min_value - margin),
            max_value + margin,
        )
        self.axis_y.setLabelFormat("%.2f")

        # Оси обязательно добавляем в этот же chart
        # до вызова attachAxis().
        self.chart.addAxis(
            self.axis_x,
            Qt.AlignmentFlag.AlignBottom,
        )
        self.chart.addAxis(
            self.axis_y,
            Qt.AlignmentFlag.AlignLeft,
        )

        # --------------------------------------------------
        # Area
        # --------------------------------------------------
        self.area_upper = QLineSeries()
        self.area_lower = QLineSeries()

        for index, value in enumerate(area_values):
            self.area_upper.append(index, value)
            self.area_lower.append(index, 0.0)

        self.area_series = QAreaSeries(
            self.area_upper,
            self.area_lower,
        )
        self.area_series.setName("Area")

        area_brush = QColor("#3498db")
        area_brush.setAlpha(100)

        self.area_series.setBrush(area_brush)
        self.area_series.setPen(
            QPen(QColor("#2471a3"), 2)
        )

        self.chart.addSeries(self.area_series)
        self.area_series.attachAxis(self.axis_x)
        self.area_series.attachAxis(self.axis_y)

        # --------------------------------------------------
        # Spline
        # --------------------------------------------------
        self.spline_series = QSplineSeries()
        self.spline_series.setName("Spline")
        self.spline_series.setPen(
            QPen(QColor("#e67e22"), 3)
        )

        for index, value in enumerate(spline_values):
            self.spline_series.append(index, value)

        self.chart.addSeries(self.spline_series)
        self.spline_series.attachAxis(self.axis_x)
        self.spline_series.attachAxis(self.axis_y)

        # --------------------------------------------------
        # Line
        # --------------------------------------------------
        self.line_series = QLineSeries()
        self.line_series.setName("Line")
        self.line_series.setPen(
            QPen(QColor("#2ecc71"), 2)
        )

        for index, value in enumerate(line_values):
            self.line_series.append(index, value)

        self.chart.addSeries(self.line_series)
        self.line_series.attachAxis(self.axis_x)
        self.line_series.attachAxis(self.axis_y)

        # --------------------------------------------------
        # Bar
        # --------------------------------------------------
        self.bar_set = QBarSet("Bar")
        self.bar_set.setColor(QColor("#9b59b6"))

        for value in bar_values:
            self.bar_set.append(value)

        self.bar_series = QBarSeries()
        self.bar_series.setName("Bar")
        self.bar_series.append(self.bar_set)
        self.bar_series.setBarWidth(0.6)

        self.chart.addSeries(self.bar_series)
        self.bar_series.attachAxis(self.axis_x)
        self.bar_series.attachAxis(self.axis_y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "График временных рядов"
        )
        self.resize(1100, 700)

        self.chart_view = TimeSeriesChart(self)

        self.chart_view.plot(
            area_values=[
                10, 13, 12, 18,
                16, 21, 19, 24,
            ],
            spline_values=[
                8, 11, 15, 13,
                19, 18, 23, 26,
            ],
            line_values=[
                5, 9, 7, 12,
                10, 15, 14, 17,
            ],
            bar_values=[
                4, 7, 5, 9,
                8, 12, 10, 13,
            ],
            categories=[
                "10:00",
                "10:05",
                "10:10",
                "10:15",
                "10:20",
                "10:25",
                "10:30",
                "10:35",
            ],
        )

        self.setCentralWidget(self.chart_view)


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()