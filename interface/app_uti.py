import datetime
from decimal import Decimal, getcontext
from PyQt6.QtGui import QStandardItem

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

    mini = {'format_prec': format_prec,
            'format_prec_order': format_prec_order,
            'min_qty': (Decimal(min_qty), get_digital(min_qty)),
            'min_price': (Decimal(min_price), get_digital(min_price)),
            'precision': (get_prec_min(precision), precision)
            }

    symbol['MINIS'] = mini
