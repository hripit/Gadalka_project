import copy
import random

from json import dumps, loads

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCharts import *
from interface.app_param import message_md, mem_app, orders_imd, orders_model, stop_thread
from interface.app_uti import compare_message, set_mini_symbols, set_symbol_id
from interface.binance_data import get_balance_info, get_all_rules, get_tradeFee
from pg_base.select_pg import get_coin, get_symbols
from interface.bi_socket import order_thread

from interface.symbol_chart import chart_param, update_chart_param
from interface.trade import Trade_wgt
import seaborn as sns

from interface.trade_back import Go_trade

params = dict()


def set_orders_model(symbols=None):
    """
    Устанавливает модель orders_model на основе данных о символах.
    :param symbols: Список или словарь символов (опционально).
    """
    # Очищаем текущую модель
    orders_model.clear()

    # Если symbols не переданы, используем глобальные данные
    if symbols is None:
        symbols = mem_app.get('params', {}).get('symbols', {}).values()

    # Устанавливаем заголовки таблицы
    orders_model.setHorizontalHeaderLabels([
        "Символ",
        "1. Взято", "Сторона", "Цена", "Получено",
        "2. Взято", "Сторона", "Цена", "Получено",
        "Период", "Доходность", "Разница цены"
    ])

    # Добавляем строки для каждого символа
    for symbol in symbols:
        ind_list = list(symbol.get('index_model', {}).values())
        if not ind_list:
            continue  # Пропускаем символы без 'index_model'

        # Преобразуем QStandardItem в список для добавления в модель
        orders_model.appendRow(ind_list)


def set_orders_imd(symbols):
    """
    Инициализирует индексы моделей для каждого символа.
    :param symbols: Словарь символов.
    """
    if not symbols or not isinstance(symbols, dict):
        raise ValueError("Переданный словарь symbols пуст или имеет некорректный тип.")

    # Определяем шаблон trades_ind_template
    trades_ind_template = {
        "Symbol": "None",
        "Pocket_out_1": "None",
        "Side_1": "None",
        "Price_1": "None",
        "Pocket_in_1": "None",
        "Pocket_out_2": "None",
        "Side_2": "None",
        "Price_2": "None",
        "Pocket_in_2": "None",
        "Interval": "None",
        "Profit": "None",
        "Spread": "None"
    }

    # Инициализируем index_model для каждого символа
    for symbol_data in symbols.values():
        if not isinstance(symbol_data, dict):
            continue  # Пропускаем некорректные символы

        # Создаем новую структуру на основе шаблона
        symbol_data["index_model"] = {}

        for key, value in trades_ind_template.items():
            # Для каждого ключа создаем новый QStandardItem
            symbol_data["index_model"][key] = QStandardItem(value)

        # Устанавливаем цвет для символа
        symbol_data["index_model"]["Symbol"].setData(
            symbol_data.get("COLOR", QColor("black")),
            Qt.ItemDataRole.ForegroundRole
        )

    # Останавливаем потоки
    mem_app['stop_thread'] = False

    # Устанавливаем модель orders_model
    set_orders_model(list(symbols.values()))

    # Запускаем потоки обработки заказов только если symbols не пуст
    if symbols:
        order_thread()


def generate_colors(symbols):
    """
    Генерирует уникальные цвета для каждого символа.

    :param symbols: Словарь символов.
    """
    num_values = len(symbols)
    palette = sns.color_palette("Spectral", n_colors=num_values)
    colors_qt = [QColor(*[int(c * 255) for c in color[:3]]) for color in palette]

    for i, symbol in enumerate(symbols.values()):
        symbol["COLOR"] = colors_qt[i % len(colors_qt)]


def get_all_symbols(coin):
    """
    Получает все доступные символы для указанной монеты.

    :param coin: Название монеты.
    :return: Словарь символов.
    """
    rules = get_all_rules()
    while not rules:
        rules = get_all_rules()

    result = [symbol for symbol in rules["symbols"]
              if symbol["status"] == "TRADING" and "LIMIT" in symbol["orderTypes"] and coin in (symbol["baseAsset"], symbol["quoteAsset"])]

    if len(result) > 10:
        pg_symbols = {x[1] for x in get_symbols("BINANCE:timeless")}
        result = [symbol for symbol in result if symbol["symbol"] in pg_symbols]

    symbol_dict = {symbol["symbol"]: symbol for symbol in result}
    for symbol in symbol_dict.values():
        set_mini_symbols(symbol)

    generate_colors(symbol_dict)
    set_symbol_id(symbol_dict)

    return symbol_dict


def init_params(coin):
    """
    Инициализирует параметры приложения для указанной монеты.
    :param coin: Название монеты.
    """
    mem_app['stop_thread'] = True

    # Инициализируем params
    params.clear()  # Очищаем старые данные
    params['coin'] = get_coin('BINANCE:timeless', coin)[0]
    if not params['coin']:
        message_md.appendRow(compare_message(f'Сбой инициализации монеты...'))
        mem_app['params'] = {'symbols': {}}  # Обеспечиваем минимальную инициализацию
        return

    message_md.appendRow(compare_message(f'Выполнена инициализация монеты {params["coin"]}'))

    # Получаем баланс
    params['balance'] = '100'  # get_balance_info(coin=params['coin'][1])['free']
    if not params['balance']:
        message_md.appendRow(compare_message(f'Отказ получения баланса по монете: {params["coin"]}'))
        mem_app['params'] = {'symbols': {}}  # Обеспечиваем минимальную инициализацию
        return

    message_md.appendRow(compare_message(f'Получен баланс по монете: {params["coin"]}, баланс: [{params["balance"]}]'))

    # Получаем все символы для монеты
    params['symbols'] = get_all_symbols(params['coin'][1])
    if not params['symbols']:
        message_md.appendRow(compare_message(f'Отказ получения информации по символам монеты: [{params["coin"]}]'))
        mem_app['params'] = {'symbols': {}}  # Обеспечиваем минимальную инициализацию
        return

    for symbol in params["symbols"].values():
        symbol["TRADES"] = {"order_1": None, "order_2": None,
                            "total": {"interval": None, "profit": None, "spread": None}}
        orders_imd[symbol["symbol"]] = {}
        symbol["socket_price"] = None
        symbol["thread"] = None
        symbol["fee"] = get_tradeFee(symbol["symbol"])[0]["makerCommission"]
        symbol["margin"] = 1 / 100
        symbol["calcu_flag"] = False

    message_md.appendRow(compare_message(f'Получена информация по символам: всего: [{len(params["symbols"])}]'))

    # Обновляем глобальную переменную mem_app
    mem_app['params'] = params

    # Очищаем старые данные
    orders_imd.clear()

    # Инициализируем индексы моделей
    set_orders_imd(params['symbols'])


def coinChanged(coin):
    init_params(coin)


def balanceChanged(balance):
    if params:
        params['balance'] = balance


class PocketVolume(QFrame):
    def __init__(self, parent=None):
        super(PocketVolume, self).__init__(parent)
        self.balance_input = None
        self.coin_combo = None
        self.update_timer = None
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.init_ui()

    def init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        label = QLabel("Pocket:")
        label.setMinimumWidth(50)

        self.coin_combo = QComboBox()
        self.coin_combo.setMinimumWidth(100)
        self.coin_combo.addItems(["WIF", "USDT", "BTC"])
        self.coin_combo.currentTextChanged.connect(lambda text: init_params(text))

        self.balance_input = QLineEdit("none")
        self.balance_input.textChanged.connect(lambda text: balanceChanged(text))

        btn = QPushButton("Start")
        btn.setFixedWidth(30)
        btn.clicked.connect(self.start_trade)

        layout.addWidget(label)
        layout.addWidget(self.balance_input)
        layout.addWidget(self.coin_combo)
        layout.addWidget(btn)

        self.setLayout(layout)
        self.setFixedHeight(40)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_wgt)
        self.update_timer.setInterval(1000)
        self.update_timer.start()

    def update_wgt(self):
        """Обновляет отображение баланса."""
        if params and params["balance"] != self.balance_input.text():
            self.balance_input.setText(params["balance"])

    def start_trade(self):
        """Запускает торговлю для выбранной монеты."""
        init_params(self.coin_combo.currentText())


def on_selection_changed(selected: QItemSelection, deselected: QItemSelection):
    """
    Обрабатывает выделение строк в таблице.

    :param selected: Выбранные элементы.
    :param deselected: Снятое выделение.
    """
    for index in selected.indexes():
        if index.column() == 0:
            row = index.row()
            symbol = orders_model.data(orders_model.index(row, 0))
            chart_param[symbol] = {}

    for index in deselected.indexes():
        if index.column() == 0:
            row = index.row()
            symbol = orders_model.data(orders_model.index(row, 0))
            chart_param.pop(symbol, None)

    update_chart_param()


class CalculateOrders(QFrame):
    def __init__(self, parent=None):
        super(CalculateOrders, self).__init__(parent)
        self.model = None
        self.table_view = None
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)

        self.init_ui()

    def init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        layout = QVBoxLayout()
        header = QLabel("Math of transaction:")
        layout.addWidget(header)

        self.table_view = QTableView()
        self.model = orders_model
        self.table_view.setModel(self.model)
        self.table_view.setSortingEnabled(True)

        for col, width in enumerate([120, 40, 120, 120, 40, 120]):
            self.table_view.setColumnWidth(col, width)

        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.MultiSelection)

        selection_model = self.table_view.selectionModel()
        selection_model.selectionChanged.connect(on_selection_changed)

        layout.addWidget(self.table_view)
        self.setLayout(layout)


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


class BottomForm(QFrame):
    def __init__(self, parent=None):
        super(BottomForm, self).__init__(parent)
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Plain)
        self.setMaximumHeight(200)

        self.init_ui()

    def init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("Press me")
        btn.clicked.connect(self.lets_trade)
        layout.addWidget(btn)

        self.setLayout(layout)

    def lets_trade(self):
        """Запускает процесс торговли."""
        mem_app["stop_thread"] = True
        Go_trade()

        offset = QPoint(30, 30)
        current_position = QPoint(self.screen_geometry.left() + 100, self.screen_geometry.top() + 100)

        for symbol in mem_app["params"]["symbols"].keys():
            new_position = current_position + offset
            current_position += offset

            dialog = Trade_wgt(parent=self, symbol=symbol, offset=new_position, screen_geometry=self.screen_geometry)
            dialog.show()


class Messages(QFrame):
    def __init__(self, parent=None):
        super(Messages, self).__init__(parent)
        self.cmb = QComboBox()
        self.lay = QHBoxLayout()
        self.lay.addWidget(self.cmb)

        self.message_model = message_md
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
