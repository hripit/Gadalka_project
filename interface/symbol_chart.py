import datetime

from PyQt6.QtCharts import *
from threading import Thread
from binance.spot import Spot
from binance.error import ClientError
import time, sys
from uti import date_now, convert_from_timestamp, dtime_range, convert_to_timestamp, repack_list
from termcolor import colored
from decimal import Decimal
import statistics
from json import dumps, loads
import websocket

import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPen, QColor

max_minutes = 60 * 3
chart_param = dict()
# Секция хранения параметров подключения API Binance
PARAMS_BI = {"api_key": None, 'api_secret': None}


def get_series_by_name(chart: QChart, series_name: str):
    """
    Возвращает серию из графика по её имени.

    :param chart: Объект QChart, содержащий серии.
    :param series_name: Имя серии для поиска.
    :return: Найденная серия или None, если серия не найдена.
    """
    for series in chart.series():  # Перебираем все серии графика
        if series.name() == series_name:  # Сравниваем имя серии
            return series
    return None


class Chart(QChart):
    def __init__(self, parent=None):
        super(Chart, self).__init__(parent)

        self.setTheme(QChart.ChartTheme.ChartThemeDark)

        # Создаем оси
        self.axis_x = QDateTimeAxis(self)
        self.axis_x.setFormat("dd.MM.yyyy hh:mm:ss")
        self.axis_x.setTitleText("Время:")
        # d_times = [datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=max_minutes+5),
        #            datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5)]
        # self.axis_x.setRange(min(d_times), max(d_times))
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setTickCount(6)  # Динамический тип меток
        self.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)

    #
        self.timer = QTimer()
    #
        self.timer.timeout.connect(self.handleTimeout)
        self.timer.setInterval(1000)
    #
        self.timer.start()
    #

    def handleTimeout(self):
        series = self.series()
        # Удалим серию если сняли выделение
        series_names = [series.name() for series in self.series()]
        for se_names in series_names:
            if se_names not in chart_param.keys():
                for series in self.series():
                    if series.name() == se_names:
                        self.removeSeries(series)

        for symbol in chart_param:
            if 'kline' not in chart_param[symbol]:
                return

            target_series = get_series_by_name(self, symbol)

            if target_series:
                kline_keys = [x for x in chart_param[symbol]['kline'].keys()]
                kline_values = [x for x in chart_param[symbol]['kline'].values()]

                xp = list()
                points = target_series.points()  # Получаем все точки серии
                for point in points:
                    xp.append(point.x())

                if not kline_keys[-1].timestamp() in xp:
                    target_series.append(kline_keys[-1].timestamp(), kline_values[-1])
                    target_series.removePoints(0, 1)

                    # Находим минимальное и максимальное значения X
                    min_x = min(points, key=lambda point: point.x()).x()
                    max_x = max(points, key=lambda point: point.x()).x()

                    min_x = convert_from_timestamp(min_x) - datetime.timedelta(minutes=5)
                    max_x = convert_from_timestamp(max_x) + datetime.timedelta(minutes=5)
                    # Обновляем диапазон оси X
                    self.axis_x.setRange(min_x, max_x)

            else:
                se = QSplineSeries(self)
                se.setName(symbol)

                axis_y = QValueAxis(self)
                axis_y.setGridLineVisible(False)
                axis_y.setLabelsVisible(False)

                # Добавляем оси к графику
                self.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                # Привязываем оси к графикам
                se.attachAxis(self.axis_x)
                se.attachAxis(axis_y)
                for line in chart_param[symbol]['kline'].items():
                    se.append(line[0].timestamp(), line[1])

                self.addSeries(se)


def get_connection_binance():
    connection = None
    try:
        connection = Spot(PARAMS_BI["api_key"], PARAMS_BI["api_secret"])
    except ClientError as error:
        print("{}: Shit came out : get_connection_binance(): "
              "{}, error code: {}, error message: {}".format(date_now,
                                                             error.status_code, error.error_code, error.error_message))

    return connection


def kline_data_1m(symbol: str, start_time: int, end_time: int):
    connection = response = None

    while not connection:
        connection = get_connection_binance()
        if not connection:
            time.sleep(1)

    try:
        response = connection.klines(symbol=symbol, interval='1m', startTime=start_time, endTime=end_time, limit=1000)

    except ClientError as error:
        print("{}: Shit came out : kline_data_1m(symbol: str, start_time: int, end_time: int): {}, error code: {}, "
              "error message: {}".format(date_now, error.status_code, error.error_code, error.error_message))

        sys.exit()

    if response:
        print(colored(f"{date_now()}: Data received: [{symbol}] ... "
                      f"[{convert_from_timestamp(response[0][0])}] ... "
                      f"[# same kline data ***********] ... length is [{len(response)}] times", 'yellow'))
    else:
        print(colored(f"{date_now()}: No data available, "
                      f"reason needs to be clarified: [{symbol}], "
                      f"[{convert_from_timestamp(start_time)}] ... [{None}] ", 'cyan'))

    return response


def kline_socket(symbol):
    def on_open_price(self):
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{self.header['symbol'].lower()}@kline_1m"],
            "id": 0
        }

        self.send(dumps(subscribe_message))
        print(colored(f"{date_now()}: Открытие kline сокета для символа [{self.header['symbol']}]"), 'green')

    def on_message_price(self, message):
        if not chart_param:
            self.close()
            return

        if self.header['symbol'] not in chart_param:
            self.close()
            return

        if chart_param[self.header['symbol']]['stop_thread']:
            self.close()
            return

        price_data = loads(message)

        if len(price_data) > 3:

            dtime = convert_from_timestamp(price_data['k']['T']).replace(second=0)
            avg_price = statistics.mean([Decimal(price_data['k']['h']), Decimal(price_data['k']['l'])])

            chart_param[self.header['symbol']]['kline'][dtime] = avg_price
            keys = list(chart_param[self.header['symbol']]['kline'].keys())
            if len(keys) > max_minutes:
                chart_param[self.header['symbol']]['kline'].pop(keys[0])


    def error_price(self, message):
        print(message, self, "kline")
        self.close()

    def close_price(self, status, message):
        print(colored(f"{date_now()}: Закрытие kline сокета для символа [{self.header['symbol']}]"), 'red')

    socket = 'wss://stream.binance.com:9443/ws'
    websocket.WebSocketApp(socket,
                           on_open=on_open_price,
                           on_message=on_message_price,
                           on_error=error_price,
                           on_close=close_price,
                           header={'symbol': symbol}
                           ).run_forever()


def chart_thread(symbol):
    # Получим данные kline по символу
    end_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1)
    start_date = end_date - datetime.timedelta(minutes=max_minutes)
    kline = (kline_data_1m(symbol, convert_to_timestamp(start_date), convert_to_timestamp(end_date)))
    kl_dict = dict()
    for line in kline:
        dtime = convert_from_timestamp(line[0])
        avg_price = statistics.mean([Decimal(line[2]), Decimal(line[3])])
        kl_dict[dtime] = avg_price

    chart_param[symbol]['kline'] = kl_dict

    chart_param[symbol]['current_deal'] = [None, None]

    chart_param[symbol]['model'] = None
    # chart_param[symbol]['stop_thread'] = False

    kline_socket(symbol)




def update_chart_param():
    for symbol in chart_param.keys():
        if 'stop_thread' not in chart_param[symbol]:
            chart_param[symbol]['stop_thread'] = False
            Thread(target=chart_thread, args=(symbol,)).start()

