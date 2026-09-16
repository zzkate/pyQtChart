import sys
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication, QMainWindow

from mixed_timeseries_chart import MixedTimeSeriesChart


def main() -> int:
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Mixed Time-Series Chart")
    window.resize(1100, 600)

    start_date = datetime(2026, 6, 7)
    dates = [start_date + timedelta(days=index) for index in range(8)]

    chart = MixedTimeSeriesChart(
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

    window.setCentralWidget(chart)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())