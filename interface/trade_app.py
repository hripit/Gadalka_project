import sys, datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCharts import *

from interface.app_param import message_md, mem_app, schema_md, layer_md
from interface.app_uti import compare_message
from interface.app_wgt import Pocket_volume, Project_GADALKA, Calculate_orders, Bottom_form, Messages, layers_cmb
from pg_base.select_pg import get_all_schema, select_layers


def set_basic_md():
    mem_app['models'] = dict()

    mem_app['models']['schemas'] = schema_md
    mem_app['models']['layers'] = layer_md


def init():
    message_md.clear()
    message_md.appendRow(compare_message('Инициализируем переменные проекта...'))
    mem_app.clear()

    message_md.appendRow(compare_message('Инициализируем доступные схемы...'))
    schemas = get_all_schema()
    for schema in schemas:
        if schema[0].find('timeless') != -1:
            mem_app[schema[0]] = dict()
            schema_md.appendRow(QStandardItem(schema[0]))

            message_md.appendRow(compare_message('Инициализируем расчетные слои...'))
            layers = select_layers(schema[0])

            if not layers:
                message_md.appendRow(compare_message(f'Для схемы: {schema} расчетные слои не обнаружены.'))
                continue

            for layer in layers:
                layer_text = (layer[0], f"symbol: {[layer[3], layer[4]]}, "
                              f"side: {[layer[5], layer[6]]}, "
                              f"base asset: {layer[1]}, margin: {layer[2]}")

                mem_app[schema[0]][layer_text] = dict()
                mem_app[schema[0]][layer_text]['default'] = layer[7]
                layer_md.appendRow(QStandardItem(layer_text[1]))

    set_basic_md()

    message_md.appendRow(compare_message('Инициализация программы успешно выполнена, можно приступать к работе...'))


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

        self.split = QSplitter()
        self.split.setOrientation(Qt.Orientation.Horizontal)

        self.left_frame = Left_frame(self)
        self.right_frame = Right_frame(self)

        self.split.addWidget(self.left_frame)
        self.split.addWidget(self.right_frame)

        self.lay.addWidget(self.split)

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
        self.setMinimumWidth(400)

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
        self.head_frame.setFixedHeight(60)

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


