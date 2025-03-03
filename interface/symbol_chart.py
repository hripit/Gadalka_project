import datetime

from PyQt6.QtCore import QDateTime, QPointF
from PyQt6.QtCharts import *
from threading import Thread

from PyQt6.QtGui import QColor
from binance.spot import Spot
from binance.error import ClientError
import time, sys
from uti import date_now, convert_from_timestamp, dtime_range, convert_to_timestamp, repack_list
from termcolor import colored
from decimal import Decimal
import statistics
from json import dumps, loads
import websocket
from interface.app_param import message_md, mem_app
from uti import date_now, convert_from_timestamp
from PyQt6.QtCore import Qt, QTimer

# from PyQt6.QtGui import QPen, QColor

max_minutes = int(60 * 16)

chart_param = dict()
# Секция хранения параметров подключения API Binance
PARAMS_BI = {"api_key": None, 'api_secret': None}


def remove_series_from_chart(chart: QChart):
    # Удалим серию если сняли выделение
    series_names = [series.objectName() for series in chart.series()]

    for se_name in series_names:
        if se_name not in chart_param.keys():
            for series in chart.series():
                if series.objectName() == se_name:
                    axes_to_remove = [axis for axis in series.attachedAxes() if isinstance(axis, QValueAxis)]
                    for axis in axes_to_remove:
                        series.detachAxis(axis)
                        chart.removeAxis(axis)
                    chart.removeSeries(series)


class Axis_X(QDateTimeAxis):
    def __init__(self, parent=None):
        super(Axis_X, self).__init__(parent)

        self.setFormat("hh:mm")
        self.setTitleText("Время:")
        self.setGridLineVisible(True)

        self.generate_range()

    def generate_range(self):
        start_dt = datetime.datetime.now() - datetime.timedelta(minutes=max_minutes)
        start_dt = start_dt.replace(second=0, minute=0, microsecond=0, tzinfo=None)

        end_dt = datetime.datetime.now() + datetime.timedelta(minutes=10)
        end_dt = end_dt.replace(second=0, microsecond=0, tzinfo=None)
        n_end_dt = end_dt.replace(minute=0, second=0, microsecond=0, tzinfo=None)

        if n_end_dt < end_dt:
            end_dt = n_end_dt + datetime.timedelta(minutes=60)
            end_dt = end_dt.replace(minute=0, second=0, microsecond=0, tzinfo=None)

        time_difference = end_dt - start_dt

        start_dt = int(start_dt.timestamp())
        start_dt = QDateTime.fromSecsSinceEpoch(start_dt)
        end_dt = int(end_dt.timestamp())
        end_dt = QDateTime.fromSecsSinceEpoch(end_dt)

        self.setRange(start_dt, end_dt)
        # Преобразуем разницу в часы, отложим тики
        hours_diff = int(abs(time_difference.total_seconds() / 3600))
        self.setTickCount(hours_diff + 1)
        colo = QColor(Qt.GlobalColor.gray)
        colo.setAlpha(80)
        self.setLinePenColor(colo)


global_axis_x = Axis_X()


class Trade_area(QAreaSeries):
    def __init__(self, symbol: str, parent=None):
        super(Trade_area, self).__init__(parent)

        self.trade = (0, 0)
        self.symbol = symbol
        # Создаем первую горизонтальную линию (верхняя граница)
        self.upper_series = QLineSeries()
        self.upper_series.append(global_axis_x.min().toSecsSinceEpoch() * 1000, 0)
        self.upper_series.append(global_axis_x.max().toSecsSinceEpoch() * 1000, 0)

        # Создаем вторую горизонтальную линию (нижняя граница)
        self.lower_series = QLineSeries()
        self.lower_series.append(global_axis_x.min().toSecsSinceEpoch() * 1000, 0)
        self.lower_series.append(global_axis_x.max().toSecsSinceEpoch() * 1000, 0)

        # Создаем область (area) между двумя линиями
        self.setObjectName(self.symbol)
        self.setLowerSeries(self.lower_series)
        self.setUpperSeries(self.upper_series)

        self.setPen(mem_app['params']['symbols'][symbol]['COLOR'])

        # Цвет заливки
        colo = mem_app['params']['symbols'][symbol]['COLOR']
        colo.setAlpha(50)
        self.setBrush(colo)

    def update(self):
        price_1 = mem_app['params']['symbols'][self.symbol]['TRADES']['order_1'][2]
        price_2 = mem_app['params']['symbols'][self.symbol]['TRADES']['order_2'][2]

        self.trade = (min(price_1, price_2), max(price_1, price_2))

        if self.lower_series.points():
            self.lower_series.removePoints(0, 2)

        self.lower_series.append(global_axis_x.min().toSecsSinceEpoch() * 1000, self.trade[0])
        self.lower_series.append(global_axis_x.max().toSecsSinceEpoch() * 1000, self.trade[0])

        if self.upper_series.points():
            self.upper_series.removePoints(0, 2)

        self.upper_series.append(global_axis_x.min().toSecsSinceEpoch() * 1000, self.trade[1])
        self.upper_series.append(global_axis_x.max().toSecsSinceEpoch() * 1000, self.trade[1])


class Axis_Y(QValueAxis):
    def __init__(self, symbol: str, min_max: list, parent=None):
        super(Axis_Y, self).__init__(parent)

        self.tol = Decimal('0.009')
        self.min_max = min_max

        self.min_value = float(Decimal(self.min_max[0]) * (Decimal('1') - self.tol))
        self.max_value = float(Decimal(self.min_max[1]) * (Decimal('1') + self.tol))

        self.symbol = symbol

        self.setTitleText(symbol)
        self.setLabelsVisible(False)
        self.setGridLineVisible(False)

        self.setRange(float(self.min_value), float(self.max_value))
        self.setTitleBrush(mem_app['params']['symbols'][symbol]['COLOR'])

    def update(self):
        self.min_value = float(Decimal(self.min_max[0]) * (Decimal('1') - self.tol))
        self.max_value = float(Decimal(self.min_max[1]) * (Decimal('1') + self.tol))

        if self.min() >= self.min_value or self.max() <= self.max_value:
            self.setRange(self.min_value, self.max_value)


def create_price_area(symbol: str, kline_data) -> QSplineSeries:
    new_series = QSplineSeries()
    new_series.setColor(mem_app['params']['symbols'][symbol]['COLOR'])

    new_series.setObjectName(symbol)

    for line in kline_data:
        point = QPointF(line[0], float(line[1]))
        new_series.append(point)

    return new_series


def update_price_series(symbol: str, price_data):
    def has_point_on_x(x_value):
        """
        Проверяет наличие точки с заданным значением X в серии.

        :param x_value: Значение X для проверки.
        :return: True, если такая точка существует, иначе False.
        """
        x = list(poi.x() for poi in series.points())
        return x_value in x

    series = chart_param[symbol]['series']['price_area']
    dt = float(price_data['k']['t'])

    avg_price = statistics.mean([Decimal(price_data['k']['l']), Decimal(price_data['k']['h'])])

    if not series.points():
        return

    if not has_point_on_x(dt):
        point = QPointF(dt, float(avg_price))
        series.append(point)

        series.removePoints(0, 1)


def get_min_max_point(symbol) -> tuple:
    trade_points = (0, 0)
    price_points = (0, 0)

    if 'price_area' in chart_param[symbol]['series']:
        price_points = list(point.y() for point in chart_param[symbol]['series']['price_area'].points())

    if 'trade_area' in chart_param[symbol]['series']:
        trade_points = (chart_param[symbol]['series']['trade_area'].trade[0],
                        chart_param[symbol]['series']['trade_area'].trade[1])

    min_value = min(min(price_points), min(trade_points))
    max_value = max(max(price_points), max(trade_points))

    return min_value, max_value


class Chart(QChart):
    def __init__(self, parent=None):
        super(Chart, self).__init__(parent)

        self.setTheme(QChart.ChartTheme.ChartThemeDark)

        # Настраиваем динамику графика по интервалу
        self.timer = QTimer()
        self.timer.timeout.connect(self.handleTimeout)
        self.timer.setInterval(1000)
        #
        self.timer.start()

    def has_axis(self, axis):
        """
        Проверяет наличие оси в графике.

        :return: True, если такая ось существует, иначе False.
        """
        all_axes = self.axes()
        if axis in all_axes:
            return True
        return False

    def has_series(self, series_obj):
        """
        Ищет серию по частичному совпадению имени.

        :param series_obj:
        :return: Найденную серию или None, если серия не найдена.
        """
        if series_obj in self.series():
            return True
        return False

    def handleTimeout(self):

        remove_series_from_chart(self)

        for symbol in chart_param:
            if 'series' in chart_param[symbol]:

                if not self.has_axis(global_axis_x):
                    self.addAxis(global_axis_x, Qt.AlignmentFlag.AlignBottom)

                if not self.has_axis(chart_param[symbol]['series']['axis_y']):
                    self.addAxis(chart_param[symbol]['series']['axis_y'], Qt.AlignmentFlag.AlignLeft)

                chart_param[symbol]['series']['axis_y'].min_max = get_min_max_point(symbol)
                chart_param[symbol]['series']['axis_y'].update()

                if not self.has_series(chart_param[symbol]['series']['price_area']):
                    self.addSeries(chart_param[symbol]['series']['price_area'])
                    chart_param[symbol]['series']['price_area'].attachAxis(global_axis_x)
                    chart_param[symbol]['series']['price_area'].attachAxis(chart_param[symbol]['series']['axis_y'])

                if not self.has_series(chart_param[symbol]['series']['trade_area']):
                    self.addSeries(chart_param[symbol]['series']['trade_area'])
                    chart_param[symbol]['series']['trade_area'].attachAxis(global_axis_x)
                    chart_param[symbol]['series']['trade_area'].attachAxis(chart_param[symbol]['series']['axis_y'])

                chart_param[symbol]['series']['trade_area'].update()

                # print(chart_param[symbol]['series']['price_area'].attachedAxes())
                # print(chart_param[symbol]['series']['trade_area'].attachedAxes())


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
        print(colored(f"{date_now()}: Открытие kline сокета для символа [{self.header['symbol']}]", 'green'))

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
            update_price_series(symbol, price_data)

    def error_price(self, message):
        print(message, self, "kline")
        self.close()

    def close_price(self, status, message):
        print(colored(f"{date_now()}: Закрытие kline сокета для символа [{self.header['symbol']}]", 'red'))

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

    kl_list = list()
    for line in kline:
        dtime = line[0]
        avg_price = statistics.mean([Decimal(line[2]), Decimal(line[3])])
        kl_list.append([dtime, avg_price])

    chart_param[symbol]['series'] = dict()
    chart_param[symbol]['series']['axis_y'] = Axis_Y(symbol, [0, 0])
    chart_param[symbol]['series']['price_area'] = create_price_area(symbol, kl_list)

    chart_param[symbol]['series']['trade_area'] = Trade_area(symbol)

    kline_socket(symbol)


def update_chart_param():
    for symbol in chart_param.keys():
        if 'stop_thread' not in chart_param[symbol]:
            chart_param[symbol]['stop_thread'] = False
            Thread(target=chart_thread, args=(symbol,)).start()
