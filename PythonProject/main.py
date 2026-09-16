import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication, QMainWindow

from mixed_timeseries_chart import MixedTimeSeriesChart


def main() -> int:
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Painter chart test")
    window.resize(1100, 600)

    start = datetime(2026, 6, 7)
    dates = [start + timedelta(days=i) for i in range(8)]

    chart = MixedTimeSeriesChart(
        area_data=[
            (dates[0], 10),
            (dates[1], 22),
            (dates[2], 34),
            (dates[3], 29),
            (dates[4], 38),
            (dates[5], 48),
            (dates[6], 55),
            (dates[7], 61),
        ],
        spline_data=[
            (dates[0], 58),
            (dates[1], 29),
            (dates[2], 18),
            (dates[3], 24),
            (dates[4], 17),
            (dates[5], 5),
            (dates[6], 18),
            (dates[7], 47),
        ],
        line_data=[
            (dates[0], 2),
            (dates[1], 18),
            (dates[2], 31),
            (dates[3], 37),
            (dates[4], 42),
            (dates[5], 48),
            (dates[6], 56),
            (dates[7], 63),
        ],
        bar_data=[
            (dates[0], 7),
            (dates[1], 12),
            (dates[2], 9),
            (dates[3], 15),
            (dates[4], 8),
            (dates[5], 13),
            (dates[6], 10),
            (dates[7], 17),
        ],
    )

    window.setCentralWidget(chart)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())