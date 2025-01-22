import sys, datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCharts import *

from interface.app_param import message_md
from interface.app_uti import compare_message
from interface.app_wgt import Pocket_volume, Project_GADALKA, Calculate_orders, Bottom_form, Messages


def init():

    message_md.clear()
    message_md.appendRow(compare_message('Инициализируем переменные проекта.'))


class Head_frame(QFrame):
    def __init__(self, parent=None):
        super(Head_frame, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.setMaximumHeight(800)

        self.lay = QHBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lay.addWidget(layers_cmb(self))
        self.lay.addWidget(Messages(self))
        self.lay.addWidget(Timer_wgt(self))

        self.setLayout(self.lay)


class layers_cmb(QFrame):
    def __init__(self, parent=None):
        super(layers_cmb, self).__init__(parent)
        self.cmb = QComboBox(self)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.cmb)

        # for symbol in params_app.vals_dict['available_symbols'].keys():
        #     self.cmb.addItem(symbol)

        self.cmb.setCurrentIndex(0)
        self.setFixedWidth(200)
        self.setLayout(self.lay)


class Timer_wgt(QFrame):
    def __init__(self, parent=None):
        super(Timer_wgt, self).__init__(parent)
        self.setFixedWidth(200)
        self.setFrameStyle(QFrame.Shadow.Plain)
        self.LCD = QLCDNumber()
        self.LCD.setDigitCount(19)
        self.LCD.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.LCD)
        self.setLayout(self.lay)
        self.time = str(datetime.datetime.now(datetime.UTC).strftime('%Y.%m.%d %H:%M:%S'))
        self.LCD.display(self.time)

        self.timer = QTimer(self)
        self.timer .timeout.connect(self.set_LCD)
        self.timer.start(99)

    def set_LCD(self):
        self.time = str(datetime.datetime.now(datetime.UTC).strftime('%Y.%m.%d %H:%M:%S'))
        self.LCD.display(self.time)


class Middle_frame(QFrame):
    def __init__(self, parent=None):
        super(Middle_frame, self).__init__(parent)

        self.lay = QHBoxLayout()
        self.left_frame = Left_frame(self)
        self.right_frame = Right_frame(self)

        self.lay.addWidget(self.left_frame)
        self.lay.addWidget(self.right_frame)

        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setLayout(self.lay)


class Left_frame(QFrame):
    def __init__(self, parent=None):
        super(Left_frame, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.lay = QVBoxLayout()
        self.lay.addWidget(Chart_form(self))

        self.setLayout(self.lay)


class Chart_form(QFrame):
    def __init__(self, parent=None, args=None):
        super(Chart_form, self).__init__(parent)
        self.args = args
        # self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setMinimumHeight(300)

        self.chart = QChartView()

        # self.chart.setChart(Kline_chart())

        self.lay = QVBoxLayout()
        self.lay.addWidget(self.chart)
        self.setLayout(self.lay)


class Right_frame(QFrame):
    def __init__(self, parent=None):
        super(Right_frame, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setFixedWidth(400)

        self.tab_bar = QTabWidget(self)
        self.lay_tab = QHBoxLayout(self)
        self.lay_tab.addWidget(self.tab_bar)

        self.tab_bar.addTab(Trade_frame(self), 'Trade')
        self.tab_bar.addTab(QFrame(self), 'Limits')

        self.setLayout(self.lay_tab)


class Trade_frame(QFrame):
    def __init__(self, parent=None):
        super(Trade_frame, self).__init__(parent)
        self.lay = QVBoxLayout()
        self.lay.addWidget(Pocket_volume(self))
        self.lay.addWidget(Calculate_orders(self))
        self.lay.addWidget(Project_GADALKA(self))
        self.lay.addWidget(Bottom_form(self))
        self.setLayout(self.lay)


class Central_frame(QFrame):
    def __init__(self, parent=None):
        super(Central_frame, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.lay = QVBoxLayout()

        self.head_frame = Head_frame(self)
        self.mid_frame = Middle_frame(self)

        self.lay.addWidget(self.head_frame)
        self.lay.addWidget(self.mid_frame)

        self.setLayout(self.lay)


class Main_window(QMainWindow):
    def __init__(self, parent=None):
        super(Main_window, self).__init__(parent)
        self.main_lay = QHBoxLayout()

        self.frame1 = Central_frame(self)

        self.setCentralWidget(self.frame1)
        self.showMaximized()


class App_kline(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setStyle('fusion')
        # self.setStyle()


def start_app():
    init()

    app = App_kline(sys.argv)
    main = Main_window()
    result = app.exec()

    sys.exit(result)


