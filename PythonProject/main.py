import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from chart_styles import APP_QSS
from mixed_timeseries_chart import MixedTimeSeriesChart


class DemoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Time-series dashboard")
        self.resize(1180, 620)

        start_date = datetime(2026, 6, 7)
        dates = [start_date + timedelta(days=i) for i in range(8)]

        area_data = [
            (dates[0], 10.0),
            (dates[1], 22.0),
            (dates[2], 34.0),
            (dates[3], 29.0),
            (dates[4], 38.0),
            (dates[5], 48.0),
            (dates[6], 55.0),
            (dates[7], 61.0),
        ]

        spline_data = [
            (dates[0], 58.0),
            (dates[1], 29.0),
            (dates[2], 18.0),
            (dates[3], 24.0),
            (dates[4], 17.0),
            (dates[5], 5.0),
            (dates[6], 18.0),
            (dates[7], 47.0),
        ]

        line_data = [
            (dates[0], 2.0),
            (dates[1], 18.0),
            (dates[2], 31.0),
            (dates[3], 37.0),
            (dates[4], 42.0),
            (dates[5], 48.0),
            (dates[6], 56.0),
            (dates[7], 63.0),
        ]

        bar_data = [
            (dates[0], 7.0),
            (dates[1], 12.0),
            (dates[2], 9.0),
            (dates[3], 15.0),
            (dates[4], 8.0),
            (dates[5], 13.0),
            (dates[6], 10.0),
            (dates[7], 17.0),
        ]

        root = QWidget()
        root.setObjectName("root")

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        self.chart = MixedTimeSeriesChart(
            area_data=area_data,
            spline_data=spline_data,
            line_data=line_data,
            bar_data=bar_data,
        )

        layout.addWidget(self.chart)
        self.setCentralWidget(root)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    window = DemoWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())