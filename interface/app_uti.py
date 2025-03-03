import datetime
import sys
from decimal import Decimal, getcontext
from PyQt6.QtGui import QStandardItem
from termcolor import colored

from pg_base.select_pg import get_coin, get_symbols

getcontext().prec = 10


def compare_message(message: str):
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return QStandardItem(f'''{dt}: {message}''')


def get_filter_value(param, symbol):
    for d, row_f in enumerate(symbol['filters'], 0):
        for roi in row_f:
            if roi == param:
                val = symbol['filters'][d][param]
                return val
    return None


def get_digital(min_num):
    s = str(min_num)
    if "." in s:
        ss = s.split(".")[1].rstrip("0")
        return len(ss)
    else:
        return 0


def get_prec_min(prec):
    if prec == 0:
        _min = '1.00000000'
        return Decimal(_min)
    else:
        _min = '0.00000000'

    _min = _min[:prec + 1] + '1'
    for _i in range(8 - prec):
        _min = _min + '0'
    return Decimal(_min)


def set_mini_symbols(symbol):
    format_prec = "{:.8f}"

    format_prec_order = "{:." + str(symbol['baseAssetPrecision']) + "f}"

    min_qty = get_filter_value('minQty', symbol)
    min_price = get_filter_value('tickSize', symbol)
    precision = get_digital(min_qty) + get_digital(min_price)
    bp = '0.' + ''.join("0" for i in range(int(symbol['baseAssetPrecision'])-1)) + "1"
    qp = '0.' + ''.join("0" for i in range(int(symbol['quoteAssetPrecision'])-1)) + "1"

    mini = {'format_prec': format_prec,
            'format_prec_order': format_prec_order,
            'min_qty': (Decimal(min_qty).normalize(), get_digital(min_qty)),
            'min_price': (Decimal(min_price).normalize(), get_digital(min_price)),
            'precision': (get_prec_min(precision).normalize(), precision),
            'baseAssetPrecision': Decimal(bp),
            'quoteAssetPrecision': Decimal(qp)
            }

    symbol['MINIS'] = mini


def set_symbol_id(symbols_dict: dict):
    def find_id():
        for pg_id in pg_data:
            if pg_id[1] == symbol:
                return pg_id[0]
        return None

    symbols_list = list(symbols_dict.keys())
    pg_data = get_symbols('BINANCE_timeless')

    for symbol in symbols_list:
        symbol_id = find_id()
        if symbol_id:
            symbols_dict[symbol]['PG_ID'] = symbol_id
            continue

        colored(print('Не найден ID символа -> ', symbol), 'red')
        sys.exit()


# Функция для преобразования Decimal в float или строку
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
