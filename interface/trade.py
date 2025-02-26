from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from interface.app_param import message_md, mem_app


class Buttons(QFrame):
    def __init__(self, parent=None):
        super(Buttons, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setFixedHeight(40)
        self.lay = QHBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.btn_done = QPushButton(self)
        self.btn_done.setFixedWidth(120)

        self.btn_cancel = QPushButton(self)
        self.btn_cancel.setFixedWidth(120)

        self.btn_refresh = QPushButton(self)
        self.btn_refresh.setFixedWidth(120)

        self.lay.addWidget(self.btn_done)
        self.lay.addWidget(self.btn_cancel)
        self.lay.addWidget(self.btn_refresh)

        self.setLayout(self.lay)


class Order_1(QFrame):
    def __init__(self, parent=None):
        super(Order_1, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.lay = QVBoxLayout()

        self.status_frame = QFrame()
        self.order_body_frame = QFrame()
        self.message_frame = QFrame()

        self.lay.addWidget(self.status_frame)
        self.lay.addWidget(self.order_body_frame)
        self.lay.addWidget(self.message_frame)


class Orders_frame(QFrame):
    def __init__(self, parent=None):
        super(Orders_frame, self).__init__(parent)

        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.symbol = self.parent().symbol  # type: ignore

        self.lay = QVBoxLayout()
        self.button_frame = Buttons(self)

        order_1 = mem_app['params']['symbols'][self.symbol]['TRADES']['order_1']
        order_2 = mem_app['params']['symbols'][self.symbol]['TRADES']['order_2']

        if order_1 and order_2:
            self.order_1_frame = Order_1(self)
            self.lay.addWidget(self.order_1_frame)

            self.order_2_frame = Order_1(self)
            self.lay.addWidget(self.order_2_frame)

        self.lay.addWidget(self.button_frame)

        self.setLayout(self.lay)


class Trade_wgt(QDialog):
    def __init__(self, symbol: str, parent=None, offset=QPoint(0, 0), screen_geometry=QRect()):
        super(Trade_wgt, self).__init__(parent)
        self.lay = QVBoxLayout()

        # Сохраняем геометрию экрана
        self.screen_geometry = screen_geometry
        # Корректируем позицию, чтобы окно не выходило за пределы экрана
        window_width = 300
        window_height = 200
        if offset.x() + window_width > self.screen_geometry.right():
            offset.setX(self.screen_geometry.left())
        if offset.y() + window_height > self.screen_geometry.bottom():
            offset.setY(self.screen_geometry.top())

        # Устанавливаем геометрию окна
        self.setGeometry(offset.x(), offset.y(), window_width, window_height)

        self.setGeometry(200 + offset.x(), 200 + offset.y(), 300, 200)  # Смещаем позицию
        self.symbol = symbol

        self.frame1 = Orders_frame(self)
        self.lay.addWidget(self.frame1)

        self.setLayout(self.lay)
        self.setWindowTitle(self.symbol)
