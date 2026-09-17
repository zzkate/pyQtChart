import sys
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget

from chart_panel import ChartPanel
from chart_styles import APP_QSS


class DemoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Mixed Time-Series Chart")
        self.resize(1100, 660)

        start_date = datetime(2026, 6, 7)

        dates = [
            start_date + timedelta(days=index)
            for index in range(8)
        ]

        self.chart_panel = ChartPanel(
            area_data=[
                (dates[0], 10.0),
                (dates[1], 22.0),
                (dates[2], 34.0),
                (dates[3], 29.0),
                (dates[4], 38.0),
                (dates[5], 48.0),
                (dates[6], 55.0),
                (dates[7], 61.0),
            ],
            spline_data=[
                (dates[0], 58.0),
                (dates[1], 29.0),
                (dates[2], 18.0),
                (dates[3], 24.0),
                (dates[4], 17.0),
                (dates[5], 5.0),
                (dates[6], 18.0),
                (dates[7], 47.0),
            ],
            line_data=[
                (dates[0], 2.0),
                (dates[1], 18.0),
                (dates[2], 31.0),
                (dates[3], 37.0),
                (dates[4], 42.0),
                (dates[5], 48.0),
                (dates[6], 56.0),
                (dates[7], 63.0),
            ],
            bar_data=[
                (dates[0], 7.0),
                (dates[1], 12.0),
                (dates[2], 9.0),
                (dates[3], 15.0),
                (dates[4], 8.0),
                (dates[5], 13.0),
                (dates[6], 10.0),
                (dates[7], 17.0),
            ],
        )

        root = QWidget()
        root.setObjectName("root")

        self.setCentralWidget(root)

        self.chart_panel.setParent(root)
        self.chart_panel.setGeometry(root.rect())

        # Кнопка остаётся дочерней графика, чтобы отображаться поверх него.
        self.edit_button = QPushButton(self.chart_panel)
        self.edit_button.setObjectName("editButton")
        #self.edit_button.setFixedSize(56, 28)
        self.edit_button.setCursor(Qt.CursorShape.ArrowCursor)
        self.edit_button.setToolTip("")

        image_path = Path(__file__).resolve().parent / "edit_button.png"

        self.edit_button.setIcon(QIcon(str(image_path)))
        self.edit_button.setIconSize(QSize(56, 28))
        self.edit_button.show()

        root.installEventFilter(self)
        QTimer.singleShot(0, self._position_edit_button)

    def _position_edit_button(self) -> None:
        """
        Размещает кнопку справа от рамки графика.

        Верхний край кнопки строго выровнен с верхней границей
        plot area внутри MixedTimeSeriesChart.
        """
        chart = self.chart_panel.chart

        # Геометрия рамки в координатах MixedTimeSeriesChart.
        plot_left = 112
        plot_top = 19
        plot_right_margin = 98

        # Координаты верхнего левого угла chart
        # переводятся из chart в координаты ChartPanel.
        plot_top_left_in_panel = chart.mapTo(
            self.chart_panel,
            chart.rect().topLeft(),
        )

        # Верхняя граница рамки графика в координатах ChartPanel.
        button_y = plot_top_left_in_panel.y() + plot_top

        # Правая граница plot area в координатах ChartPanel.
        plot_right = (
                plot_top_left_in_panel.x()
                + chart.width()
                - plot_right_margin
        )

        # Правая свободная панель имеет ширину 98 px.
        # Кнопка шириной 76 px центрируется внутри неё.
        button_x = int(
            plot_right
            + (plot_right_margin - self.edit_button.width()) / 2
        )

        self.edit_button.move(
            max(0, button_x),
            max(0, button_y),
        )

        self.edit_button.raise_()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.centralWidget():
            if event.type() == event.Type.Resize:
                self.chart_panel.setGeometry(
                    self.centralWidget().rect()
                )
                self._position_edit_button()

        return super().eventFilter(watched, event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    window = DemoWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())