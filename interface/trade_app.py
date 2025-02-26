import sys
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QPainter, QStandardItem
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFrame, QHBoxLayout, QVBoxLayout, QSplitter,
    QTabWidget, QLCDNumber, QMessageBox, QPushButton
)
from PyQt6.QtCharts import QChart, QChartView
from interface.app_param import mem_app
from interface.app_wgt import PocketVolume, CalculateOrders, BottomForm, Messages, layers_cmb
from interface.symbol_chart import Chart
from initialize import initialize_project


# Базовый класс для фреймов с общей конфигурацией
class BaseFrame(QFrame):
    def __init__(self, parent=None, style=QFrame.Shape.Panel | QFrame.Shadow.Plain):
        super().__init__(parent)
        self.setFrameStyle(style)


# Верхняя панель с таймером и сообщениями
class HeadFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(80)
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(layers_cmb(self))
        layout.addWidget(Messages(self))
        layout.addWidget(TimerWidget(self))
        self.setLayout(layout)


# Виджет таймера
class TimerWidget(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent, style=QFrame.Shadow.Plain)
        self.setFixedWidth(200)
        layout = QHBoxLayout()
        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(19)
        self.lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        layout.addWidget(self.lcd)
        self.setLayout(layout)
        self.update_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Обновление каждую секунду

    def update_time(self):
        current_time = QDateTime.currentDateTimeUtc().toString('yyyy.MM.dd HH:mm:ss')
        self.lcd.display(current_time)


# Центральный фрейм с верхней панелью и основным содержимым
class CentralFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.head_frame = HeadFrame(self)
        self.head_frame.setFixedHeight(60)
        self.middle_frame = MiddleFrame(self)
        layout.addWidget(self.head_frame)
        layout.addWidget(self.middle_frame)
        self.setLayout(layout)


# Фрейм с двумя частями: график слева и панель управления справа
class MiddleFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(LeftFrame(self))
        splitter.addWidget(RightFrame(self))
        layout.addWidget(splitter)
        self.setLayout(layout)


# Левая часть с графиком
class LeftFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addWidget(ChartForm(self))
        self.setLayout(layout)


# Правая часть с вкладками
class RightFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        tab_widget = QTabWidget()
        tab_widget.addTab(TradeFrame(self), 'Trade')
        tab_widget.addTab(QFrame(), 'Limits')  # Пустая вкладка для примера
        layout.addWidget(tab_widget)
        self.setLayout(layout)


# Форма графика
class ChartForm(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.chart = Chart()
        self.chart.setTitle("Dynamic average prices:")
        self.chart.legend().hide()
        self.chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        chart_view = QChartView(self.chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setRubberBand(QChartView.RubberBand.HorizontalRubberBand)

        # Кнопка для восстановления графика
        self.reset_button = QPushButton("Восстановить")
        self.reset_button.clicked.connect(self.reset_chart)

        layout = QVBoxLayout()
        layout.addWidget(chart_view)
        layout.addWidget(self.reset_button)
        self.setLayout(layout)

    def reset_chart(self):
        """Сброс графика к исходному состоянию."""
        self.chart.zoomReset()  # Сброс масштаба


# Форма торговли
class TradeFrame(BaseFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.addWidget(PocketVolume(self))
        layout.addWidget(CalculateOrders(self))
        layout.addWidget(BottomForm(self))
        self.setLayout(layout)


# Основное окно приложения
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.central_frame = CentralFrame(self)
        self.setCentralWidget(self.central_frame)
        self.showMaximized()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы действительно хотите закрыть это окно?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            mem_app['stop_thread'] = True
            event.accept()
            print("Окно закрывается...")
        else:
            event.ignore()
            print("Закрытие отменено.")


# Запуск приложения
class AppKline(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setStyle('fusion')


def start_app():
    initialize_project()
    app = AppKline(sys.argv)
    main = MainWindow()
    result = app.exec()
    sys.exit(result)