from binance.spot import Spot
from binance.error import ClientError
from parameters import PARAMS_BI
from uti import date_now


def get_connection_binance():
    connection = None
    try:
        connection = Spot(PARAMS_BI["api_key"], PARAMS_BI["api_secret"])
    except ClientError as error:
        print("{}: Хуйня вышла-с get_connection_binance(): "
              "{}, error code: {}, error message: {}".format(date_now,
                                                             error.status_code, error.error_code, error.error_message))

    return connection


def kline_data_1m(symbol: str, start_time: int, end_time: int):
    connection = None
    while not connection:
        connection = get_connection_binance()

    try:
        response = connection.klines(symbol=symbol, interval='1m', startTime=start_time, endTime=end_time, limit=1000)
    except ClientError as error:
        print("{}: Хуйня вышла-с kline_data_1m(symbol: str, start_time: int, end_time: int): {}, error code: {}, "
              "error message: {}".format(date_now, error.status_code, error.error_code, error.error_message))
        response = None

    if response:
        print(f"{date_now()}: Получены данные: [{symbol}] ... [{response[0][0]}] ... [{response[0][9]}] ")
    else:
        print(f"{date_now()}: Данные отсутствуют, необходима ручная проверка: [{symbol}], [{start_time}] ... [{None}] ")

    return response
###
