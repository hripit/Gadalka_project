import copy
import random

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCharts import *
from interface.app_param import message_md, mem_app, orders_imd, orders_model, stop_thread
from interface.app_uti import compare_message, set_mini_symbols
from interface.binance_data import get_balance_info, get_all_rules, get_tradeFee
from pg_base.select_pg import get_coin, get_symbols
from interface.bi_socket import order_thread

from interface.symbol_chart import chart_param, update_chart_param

params = dict()


def set_orders_model():
    orders_model.clear()

    orders_model.setHorizontalHeaderLabels(["Symbol",
                                            "ORDER_ID", "Pocket_out", "Side", "Price", "Status", "Pocket_in",
                                            "ORDER_ID", "Pocket_out", "Side", "Price", "Status", "Pocket_in",
                                            "Interval", "Profit", "Spread"])
    for symbol in mem_app['params']['symbols'].values():
        ind_list = list(symbol['index_model'].values())
        orders_model.appendRow(ind_list)


def set_orders_imd():
    trades_ind = dict()

    for symbol in mem_app['params']['symbols'].values():
        symbol['index_model'] = copy.deepcopy(trades_ind)
        symbol['index_model']['Symbol'] = QStandardItem('None')
        symbol['index_model']['Symbol'].setData(symbol['COLOR'], Qt.ItemDataRole.ForegroundRole)

        symbol['index_model']['FIRST_ORDER'] = QStandardItem('...')
        symbol['index_model']['Pocket_out_1'] = QStandardItem('None')
        symbol['index_model']['Side_1'] = QStandardItem('None')
        symbol['index_model']['Price_1'] = QStandardItem('None')
        symbol['index_model']['Status_1'] = QStandardItem('None')
        symbol['index_model']['Pocket_in_1'] = QStandardItem('None')
        symbol['index_model']['SECOND_ORDER'] = QStandardItem('...')
        symbol['index_model']['Pocket_out_2'] = QStandardItem('None')
        symbol['index_model']['Side_2'] = QStandardItem('None')
        symbol['index_model']['Price_2'] = QStandardItem('None')
        symbol['index_model']['Status_2'] = QStandardItem('None')
        symbol['index_model']['Pocket_in_2'] = QStandardItem('None')
        symbol['index_model']['Interval'] = QStandardItem('None')
        symbol['index_model']['Profit'] = QStandardItem('None')
        symbol['index_model']['Spread'] = QStandardItem('None')

    mem_app['stop_thread'] = False

    set_orders_model()

    order_thread()


def generate_colors(symbols):
    """Генерирует уникальные цвета для каждого значения из списка."""
    num_values = len(symbols)
    for i, symbol in enumerate(symbols):
        # Генерируем случайный цвет
        # Генерируем цвет на основе индекса элемента
        hue = (i * 360) // num_values  # Распределяем оттенки равномерно по всему кругу
        saturation = 255  # Максимальная насыщенность
        value_level = 200  # Яркость

        color = QColor()
        color.setHsv(hue, saturation, value_level)

        symbols[symbol]['COLOR'] = color


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

    if len(symbols) > 10:
        # оставим только "нужные" символы
        pg_symbols = get_symbols('BINANCE:timeless')
        pg_symbols = [x[1] for x in pg_symbols]

        symbols = [n for n in symbols if n['symbol'] in pg_symbols]

    symbol_dict = dict()
    for symbol in symbols:
        symbol_dict[symbol['symbol']] = symbol

    generate_colors(symbol_dict)

    return symbol_dict


def init_params(coin):
    mem_app['stop_thread'] = True

    params['coin'] = get_coin('BINANCE:timeless', coin)[0]
    if not params['coin']:
        message_md.appendRow(compare_message(f'Сбой инициализации монеты...'))
        return
    message_md.appendRow(compare_message(f'Выполнена инициализация монеты {params['coin']}'))

    # params['balance'] = get_balance_info(coin=params['coin'][1])['free']
    params['balance'] = '100'
    if not params['balance']:
        message_md.appendRow(compare_message(f'Отказ получения баланса по монете: {params['coin']}'))
        return
    message_md.appendRow(compare_message(f'Получен баланс по монете: {params['coin']}, баланс:  '
                                         f'[{params['balance']}]'))

    # symbols = get_balance_info(coin=None)
    params['symbols'] = get_all_symbols(params['coin'][1])

    if not params['symbols']:
        message_md.appendRow(compare_message(f'Отказ получения информации по символам монеты: [{params['coin']}]'))
        return

    message_md.appendRow(compare_message(f'Получена информация по символам : '
                                         f'всего: [{len(params['symbols'])}]'))
    orders_imd.clear()

    for symbol in params['symbols'].values():
        order_dict = None

        symbol['TRADES'] = {'order_1': copy.deepcopy(order_dict), 'order_2': copy.deepcopy(order_dict)}
        symbol['TRADES']['total'] = {'interval': None, 'profit': None, 'spread': None}

        orders_imd[symbol['symbol']] = dict()
        symbol['socket_price'] = None
        symbol['thread'] = None

        symbol['fee'] = get_tradeFee(symbol['symbol'])[0]['makerCommission']
        symbol['margin'] = 0.2 / 100
        symbol['calcu_flag'] = False

    mem_app['params'] = params

    set_orders_imd()


def coinChanged(coin):
    init_params(coin)


def balanceChanged(balance):
    if params:
        params['balance'] = balance


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
        self.coin.currentTextChanged.connect(coinChanged)

        self.balance = QLineEdit(self)
        self.balance.setText('none')
        self.balance.textChanged.connect(balanceChanged)
        # self.value.setMinimumWidth(80)

        self.btn = QPushButton()
        self.btn.setFixedWidth(30)
        self.btn.clicked.connect(self.start_trade)

        self.lay.addWidget(self.label)
        self.lay.addWidget(self.balance)
        self.lay.addWidget(self.coin)
        self.lay.addWidget(self.btn)

        self.setLayout(self.lay)
        self.setFixedHeight(40)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_wgt)
        self.update_timer.setInterval(1000)
        self.update_timer.start()

    def update_wgt(self):
        if params:
            if not params['balance'] == self.balance.text():
                self.balance.setText(params['balance'])

    def start_trade(self):
        init_params(self.coin.currentText())


# Шаг 2: Обработчик события выделения и снятия выделения
def on_selection_changed(selected: QItemSelection, deselected: QItemSelection):
    # Обработка выделения строк

    for index in selected.indexes():
        if index.column() == 0:
            row = index.row()
            symbol = orders_model.data(orders_model.index(row, 0))
            chart_param[symbol] = dict()

    for index in deselected.indexes():
        if index.column() == 0:
            row = index.row()
            symbol = orders_model.data(orders_model.index(row, 0))
            chart_param[symbol]['stop_thread'] = True

            chart_param.pop(symbol)

    update_chart_param()


class Calculate_orders(QFrame):
    def __init__(self, parent=None):
        super(Calculate_orders, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        # self.setMaximumHeight(200)
        self.header_text = QLabel('Math of transaction :')
        self.lay = QVBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.table_view = QTableView(self)
        self.model = orders_model

        self.table_view.setModel(self.model)
        self.table_view.setSortingEnabled(True)

        self.table_view.setColumnWidth(2, 120)
        self.table_view.setColumnWidth(3, 40)
        self.table_view.setColumnWidth(6, 120)
        self.table_view.setColumnWidth(8, 120)
        self.table_view.setColumnWidth(9, 40)
        self.table_view.setColumnWidth(12, 120)

        # Настройка режима выделения для выделения всей строки
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.MultiSelection)

        # Настройка горизонтального заголовка
        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setDefaultSectionSize(80)
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Подключаем обработчик события выделения
        selection_model = self.table_view.selectionModel()
        selection_model.selectionChanged.connect(on_selection_changed)

        self.lay.addWidget(self.header_text)
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
        self.setMinimumHeight(200)

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
        self.red_btn.clicked.connect(self.lets_trade)

        self.lay.addWidget(self.red_btn)
        self.setLayout(self.lay)

    def lets_trade(self):
        mem_app['stop_thread'] = True


class Messages(QFrame):
    def __init__(self, parent=None):
        super(Messages, self).__init__(parent)
        self.cmb = QComboBox(self)
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.cmb)

        self.message_model = message_md
        # self.message_model.setItem(0,0,QStandardItem('Текстовые сообщения программы....'))
        self.cmb.setModel(self.message_model)

        self.cmb.setCurrentIndex(message_md.rowCount() - 1)
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
