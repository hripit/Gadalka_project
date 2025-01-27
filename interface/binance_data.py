from binance.spot import Spot
from binance.error import ClientError
from uti import date_now
from interface.data_file import get_connection_binance


def get_all_rules(sym: str = None):
    connection = get_connection_binance()
    print(f'{date_now()}: Запросим данные данные биржи о правилах торговли: [{sym}]')
    try:
        if sym:
            response = connection.exchange_info(symbol=sym)
        else:
            response = connection.exchange_info()
    except ClientError as error:
        print("Хуйня вышла-с set_rules(pair): {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message))
        response = None
    return response


def get_balance_info(coin=None):
    i = 0
    response = list()

    connection = get_connection_binance()
    while not connection:
        connection = get_connection_binance()
    print(f'{date_now()}: Запросим данные с биржи о балансе по монете: [{coin}]')
    try:
        balance = connection.coin_info()
        if coin:
            for sy in balance:
                if sy["coin"] == coin:
                    break
                i = i + 1
            response = balance[i]
        else:
            for row in balance:
                if not row['free'] == '0':
                    response.append(row)

    except ClientError as error:
        print("Хуйня вышла-с get_balance_info(): {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message), )
        response = {}

    return response
