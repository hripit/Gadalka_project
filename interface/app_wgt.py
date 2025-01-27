from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCharts import *
from interface.app_param import message_md, mem_app
from interface.app_uti import compare_message, set_mini_symbols
from interface.binance_data import get_balance_info, get_all_rules


def focuses_md():
    print(1)


def get_all_symbols(coin):
    symbols = list()

    rules = get_all_rules()
    while not rules:
        rules = get_all_rules()

    result = rules['symbols']
    for val in result:
        if not val['status'] == 'TRADING':
            continue
        if 'LIMIT' not in val['orderTypes']:
            continue
        if coin not in (val['baseAsset'], val['quoteAsset']):
            continue

        set_mini_symbols(val)
        symbols.append(val)
    return symbols


class Pocket_volume(QFrame):
    def __init__(self, parent=None):
        super(Pocket_volume, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.lay = QHBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.label = QLabel('Pocket:')
        self.label.setMinimumWidth(50)

        self.coin = QComboBox(self)
        self.coin.setMinimumWidth(100)
        self.coin_model = QStandardItemModel()
        self.coin_model.appendRow(QStandardItem('WIF'))
        self.coin_model.appendRow(QStandardItem('USDT'))

        self.coin.setModel(self.coin_model)

        self.value = QLineEdit(self)
        # self.value.setMinimumWidth(80)

        self.btn = QPushButton()
        self.btn.setFixedWidth(30)
        self.btn.clicked.connect(self.start_trade)

        self.lay.addWidget(self.label)
        self.lay.addWidget(self.value)
        self.lay.addWidget(self.coin)
        self.lay.addWidget(self.btn)

        self.setLayout(self.lay)
        self.setFixedHeight(40)

    def start_trade(self):
        params = dict()
        params['coin'] = [None, self.coin.currentText()]

        params['balance'] = get_balance_info(coin=params['coin'][1])
        if not params['balance']:
            return
        message_md.appendRow(compare_message(f'Получен баланс по монете: [{params['coin']}], '
                                             f'[{params['balance']['free']}]'))

        # symbols = get_balance_info(coin=None)
        params['symbols'] = get_all_symbols(params['coin'][1])

        if not params['symbols']:
            return

        message_md.appendRow(compare_message(f'Получена информация по символам : '
                                             f'[{params['symbols'][0]['symbol']}] ... '
                                             f'[{params['symbols'][-1]['symbol']}], '
                                             f'всего: [{len(params['symbols'])}]'))
        print(params['coin'])


class Calculate_orders(QFrame):
    def __init__(self, parent=None):
        super(Calculate_orders, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        # self.setMaximumHeight(200)
        self.header_text = QLabel('Math of transaction :')
        self.lay = QVBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.table_model = QStandardItemModel()
        self.table_model.setColumnCount(3)
        self.table_model.setRowCount(4)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.table_model)

        self.lay.addWidget(self.header_text )
        self.lay.addWidget(self.table_view)

        self.setLayout(self.lay)


class Project_GADALKA(QFrame):
    def __init__(self, parent=None):
        super(Project_GADALKA, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        # self.setMaximumHeight(200)

        self.lay = QVBoxLayout()
        self.header_text = QLabel('@BIT_GADALKA')
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.table_model = QStandardItemModel()
        self.table_model.setColumnCount(3)
        self.table_model.setRowCount(4)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.table_model)
        self.lay.addWidget(self.header_text)
        self.lay.addWidget(self.table_view)
        self.setLayout(self.lay)


class Bottom_form(QFrame):
    def __init__(self, parent=None):
        super(Bottom_form, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setMaximumHeight(200)

        self.lay = QVBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        self.red_btn = QPushButton('Press me')

        self.lay.addWidget(self.red_btn)
        self.setLayout(self.lay)


class Messages(QFrame):
    def __init__(self, parent=None):
        super(Messages, self).__init__(parent)
        self.cmb = QComboBox(self)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.cmb)

        self.message_model = message_md
        # self.message_model.setItem(0,0,QStandardItem('Текстовые сообщения программы....'))
        self.cmb.setModel(self.message_model)

        self.cmb.setCurrentIndex(message_md.rowCount()-1)
        self.setMinimumWidth(200)
        self.setLayout(self.lay)


class layers_cmb(QFrame):
    def __init__(self, parent=None):
        super(layers_cmb, self).__init__(parent)
        self.cmb = QComboBox(self)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.cmb)
        self.cmb.setModel(mem_app['models']['layers'])

        self.cmb.setCurrentIndex(0)  # Потом будем ставить по умолчанию...

        self.cmb.currentIndexChanged.connect(self.index_changed)

        self.setFixedWidth(200)
        self.setLayout(self.lay)

    def index_changed(self, item):
        message_md.appendRow(compare_message(f'Установлен слой: {self.cmb.currentText()}'))
        print(item)



