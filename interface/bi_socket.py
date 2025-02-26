import datetime
import time

import websocket
import threading

from json import dumps, loads

from PyQt6.QtGui import QStandardItem, QBrush, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget

from uti import date_now

from interface.app_param import message_md, mem_app
from interface.app_uti import compare_message
from interface.calcu import calculate_deals

green = QBrush(QColor('green'))
red = QBrush(QColor('red'))


def trade_operation(symbol):
    calculate_deals(pocket=(mem_app['params']['balance'], mem_app['params']['coin']),
                    symbol=mem_app['params']['symbols'][symbol])

    update_model(symbol)


def update_model(symbol):
    if (mem_app['params']['symbols'][symbol]['TRADES']['order_1'] and
            mem_app['params']['symbols'][symbol]['TRADES']['order_2']):

        order_1 = mem_app['params']['symbols'][symbol]['TRADES']['order_1']
        order_2 = mem_app['params']['symbols'][symbol]['TRADES']['order_2']

        total = mem_app['params']['symbols'][symbol]['TRADES']['total']

        index_model = mem_app['params']['symbols'][symbol]['index_model']

        color_1 = green if order_1[3] == 'BUY' else red
        color_2 = green if order_2[3] == 'BUY' else red

        index_model['Symbol'].setText(str(symbol))
        index_model['Pocket_out_1'].setText(str(order_1[0]))
        index_model['Side_1'].setText(order_1[3])
        index_model['Side_1'].setData(color_1, Qt.ItemDataRole.ForegroundRole)
        index_model['Price_1'].setText(str(order_1[2]))
        index_model['Pocket_in_1'].setText(str(order_1[6][0]))
        #######
        index_model['Pocket_out_2'].setText(str(order_2[0]))
        index_model['Side_2'].setText(str(order_2[3]))
        index_model['Side_2'].setData(color_2, Qt.ItemDataRole.ForegroundRole)
        index_model['Price_2'].setText(str(order_2[2]))
        index_model['Pocket_in_2'].setText(str(order_2[6]))
        index_model['Interval'].setText(str(datetime.timedelta(0)))
        index_model['Profit'].setText(str(total['profit']))
        index_model['Spread'].setText(str(total['spread']))


def price_socket(symbol):
    def on_open_price(self):
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{self.header['symbol'].lower()}@depth5@1000ms"],
            "id": 0
        }

        self.send(dumps(subscribe_message))

    def on_message_price(self, message):
        if mem_app['stop_thread']:
            self.close()

        price_data = loads(message)

        if len(price_data) == 3:
            # print(f"{datetime.datetime.now()}: price [{self.header['symbol']}] ")
            mem_app['params']['symbols'][symbol]['socket_price'] = price_data

            trade_operation(symbol)

    def error_price(self, message):
        print(message, self, "price")
        self.close()

    def close_price(self, status, message):
        mem_app['params']['symbols'][symbol]['socket_price'] = None
        print(f"{date_now()}: Закрытие price сокета для символа [{self.header['symbol']}], {status, message}")

    socket = 'wss://stream.binance.com:9443/ws'
    websocket.WebSocketApp(socket,
                           on_open=on_open_price,
                           on_message=on_message_price,
                           on_error=error_price,
                           on_close=close_price,
                           header={'symbol': symbol}
                           ).run_forever()


def order_thread():
    for symbol in mem_app['params']['symbols']:
        price_thread = threading.Thread(target=price_socket, args=(symbol,))
        price_thread.start()

        # trade_thread = threading.Thread(target=trade_operation, args=(symbol,))
        # trade_thread.start()
