import sys
import time

from pg_base.select_pg import get_trader_protokol
from pg_base.update_pg import update_order_by_id

from threading import Thread
from uti import date_now
from json import dumps, loads
import websocket
from interface.data_file import get_connection_binance
from binance.error import ClientError
from binance.spot import Spot
from termcolor import colored

mem_app = dict()
mem_app['deals'] = dict()


def get_id(status) -> int:
    match status:
        case 'NEW':
            return 1
        case 'FILLED':
            return 2
        case 'CANCELED':
            return 3
        case 'PARTIALLY_FILLED':
            return 4
        case 'ERROR':
            return 99
    return 0


def get_order_data(__symbol, order_id):
    bi_client = get_connection_binance()
    try:
        response = bi_client.get_order(symbol=__symbol, orderId=order_id)
    except ClientError as error:
        print("\r        Хуйня вышла-с get_order_data(): {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message))
        response = None
    return response


def set_0_order(json) -> dict:
    connection = get_connection_binance()
    try:
        response = connection.new_order(**json)
        # response = {
        #     "symbol": "BUSDUSDT",
        #     "orderId": 944448897,
        #     "orderListId": -1,
        #     "clientOrderId": "electron_0cb02285f95d48e9ab0e2602801",
        #     "price": "1.00320000",
        #     "origQty": "524.00000000",
        #     "executedQty": "524.00000000",
        #     "cummulativeQuoteQty": "523.68560000",
        #     "status": "NEW"
        # }
    except ClientError as error:
        colored(print("\rХуйня вышла-с set_0_order(param): {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message), json), 'red')

        response = 'ERROR'

    return response

    # response = {
    #     "symbol": "BUSDUSDT",
    #     "orderId": 944448897,
    #     "orderListId": -1,
    #     "clientOrderId": "electron_0cb02285f95d48e9ab0e2602801",
    #     "price": "1.00320000",
    #     "origQty": "524.00000000",
    #     "executedQty": "524.00000000",
    #     "cummulativeQuoteQty": "523.68560000",
    #     "status": "NEW"
    # }


def set_watcher(order, symbol, order_id):
    response = get_order_data(symbol, order_id)

    response = {
        "symbol": "BUSDUSDT",
        "orderId": 944448897,
        "orderListId": -1,
        "clientOrderId": "electron_0cb02285f95d48e9ab0e2602801",
        "price": "1.00320000",
        "origQty": "524.00000000",
        "executedQty": "524.00000000",
        "cummulativeQuoteQty": "523.68560000",
        "status": "NEW"
    }

    update_order_by_id(schema='BINANCE:timeless', order_id=order[0],
                       status_id=get_id(response['status']), body_json=dumps(response), platform_uid=order_id)

    while response['status'] not in ('CANCELED', 'FILLED'):
        response = get_order_data(symbol, order_id)

        response = {
            "symbol": "BUSDUSDT",
            "orderId": 944448897,
            "orderListId": -1,
            "clientOrderId": "electron_0cb02285f95d48e9ab0e2602801",
            "price": "1.00320000",
            "origQty": "524.00000000",
            "executedQty": "524.00000000",
            "cummulativeQuoteQty": "523.68560000",
            "status": "FILLED"
        }

        update_order_by_id(schema='BINANCE:timeless', order_id=order[0],
                           status_id=get_id(response['status']), body_json=dumps(response), platform_uid=order_id)

        order[2] = order_id
        order[3] = [get_id(response['status']), response['status']]

        if response['status'] not in ('CANCELED',):
            print(f'{date_now()}: Фиксируем отмену ордера ->> [{order}] <<- [{response['status']}]')
            break

        if response['status'] not in ('CANCELED', 'FILLED'):
            time.sleep(1)


def set_first_deal(order):
    response = set_0_order(order[1])

    if response == 'ERROR':
        print(f'{date_now()}: Ошибка установки ордера: ->> [{order[0]}] <<- Поток остановлен. '
              f'\n Торговая операция помечена ошибкой')

        update_order_by_id(schema='BINANCE:timeless', order_id=order[0],
                           status_id=get_id('ERROR'), body_json=None, platform_uid=None)
        sys.exit()

    set_watcher(order, response['symbol'], response['orderId'])


# response = {
#     "symbol": "BUSDUSDT",
#     "orderId": 944448897,
#     "orderListId": -1,
#     "clientOrderId": "electron_0cb02285f95d48e9ab0e2602801",
#     "price": "1.00320000",
#     "origQty": "524.00000000",
#     "executedQty": "524.00000000",
#     "cummulativeQuoteQty": "523.68560000",
#     "status": "NEW"
# }


def trade_job_thread(trade):
    first_order = mem_app['deals'][trade]['first_order']
    second_order = mem_app['deals'][trade]['second_order']

    match first_order[3][1]:
        case 'ERROR':
            if second_order[3][1] == 'NONE':
                update_order_by_id(schema='BINANCE:timeless', order_id=second_order[0], status_id=99,
                                   body_json=None, platform_uid=None)
                sys.exit()

        case 'NONE':
            print(first_order[3][1])
        case 'NEW' | 'PARTIALLY_FILLED':
            print(first_order[3][1])
        case 'FILLED':
            print(first_order[3][1])
        case 'CANCELED':
            print(first_order[3][1])

    match second_order[3][1]:
        case 'ERROR':
            print(second_order[3][1])
        case 'NONE':
            print(second_order[3][1])
        case 'NEW' | 'PARTIALLY_FILLED':
            print(second_order[3][1])
        case 'FILLED':
            print(second_order[3][1])
        case 'CANCELED':
            print(second_order[3][1])


    if first_order[3][1] == 'ERROR' and second_order[3][1] == 'NONE':
        print(f'{date_now()}: Отменяем дальнейшую тогровую сделку..')

    if first_order[3][1] == 'NONE' and second_order[3][1] == 'NONE':
        print(f'{date_now()}: Нормальное явление... проводим полный цикл торговой операции...')
    # 99
    # "ERROR"
    # 0
    # "NONE"
    # 1
    # "NEW"
    # 2
    # "FILLED"
    # 3
    # "CANCELED"
    # 4
    # "PARTIALLY_FILLED"

    print(f'{date_now()}: Закрываем поток')
    sys.exit()

    #
    #
    #
    # trade = mem_app['deals'][trade]
    # # продумать логику если пришло говно.
    #
    # # Обрабатываем статусы ордеров...
    # match trade['first_order'][3][1]:
    #     case 'ERROR':
    #         # По какой-то причине, ранее произошел сбой, однако второй ордер "живой"...
    #         # Ставим отметку ERROR
    #         print(f'{date_now()}: По какой-то причине, ранее произошел сбой первый ордер помечен "Ошибка"... -->>')
    #         print(f"{date_now()}: Ставим отметку {'''Ошибка'''} -->> [{trade['second_order'][0]}]"
    #               f" <<-- Останавливаем поток. ")
    #         update_order_by_id(schema='BINANCE:timeless', order_id=trade['second_order'][0], status_id=99,
    #                            body_json=None, platform_uid=None)
    #         sys.exit()
    #     case 'NONE':
    #         # Логика следующая: Первый ордер получается не ставили...
    #         # Нужно создать первый ордер, дождаться его исполнения...
    #         # И перейти ко второму ордеру.
    #         set_first_deal(trade['first_order'])
    #         print(f'{date_now()}: Начнем отслеживать прайс второго ордера... -->>')
    #     case 'NEW' | 'PARTIALLY_FILLED':
    #         # Логика следующая: Первый ордер установили ранее...
    #         # Начнем отслеживать его полное исполнение.
    #         set_watcher(trade['first_order'], trade['symbol'][1], trade['first_order'][2])
    #     case 'FILLED':
    #         # Логика следующая: Первый ордер установили ранее...
    #         # ... но по какой-то причине второй ордер не исполен, что ведет к потенциальным убыткам
    #         # ... преходим ко второму ордеру.
    #         print(f'{date_now()}: Первый ордер установили ранее, он исполнен... -->> {trade['first_order'][0]} '
    #               f'\n {trade['first_order'][1]}')
    #     case 'CANCELED':
    #         # Логика следующая: Первый ордер установили ранее...
    #         # По какой-то причине исполнение прекратили, отменим и второй ордер...
    #         update_order_by_id(schema='BINANCE:timeless', order_id=trade['second_order'][0], status_id=3,
    #                            body_json=None, platform_uid=None)
    #
    # match trade['second_order'][3][1]:
    #     case 'ERROR':
    #         # что делать в этом случае делать непонятно.
    #         print(trade['first_order'])
    #         print(trade['second_order'])
    #         sys.exit()
    #     case 'NONE':
    #         # Логика следующая: Первый ордер установили ранее, он исполнен...
    #         # Откроем наблюдение за прайсом, если все норм... завершаем сделку.
    #         if trade['first_order'][3][0] == 2:  # FILLED
    #             print(f'{date_now()}: Отслеживаем прайс второго ордера... ')
    #     case 'NEW' | 'PARTIALLY_FILLED' | 'FILLED':
    #         # Логика следующая: Второй ордер установили ранее, он в работе...
    #         # Запускаем наблюдение за исполнением.
    #         set_watcher(trade['second_order'], trade['symbol'][1], trade['second_order'][2])
    #     case 'CANCELED':
    #         if not trade['first_order'][3][0] == 3:  # CANCELED
    #             # Логика следующая: Что-то произошло ордер отменили...
    #             # Что делать в этом случае непонятно.
    #             print(trade['first_order'])
    #             print(trade['second_order'])
    #             sys.exit()
    #
    # print(f'{date_now()}: Торговая операция успешно завершена... ')
    # print(trade['first_order'])
    # print(trade['second_order'])


def price_socket(__symbol: str):
    def on_open_price(self):
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{self.header['symbol'].lower()}@depth5@1000ms"],
            "id": 0
        }

        self.send(dumps(subscribe_message))

    def on_message_price(self, message):
        # if mem_app['stop_thread']:
        #     self.close()

        price_data = loads(message)

        if len(price_data) == 3:
            print(f"{date_now()}: head: [{self}] price [{price_data}] ")

    def error_price(self, message):
        print(message, self, "price")
        self.close()

    def close_price(self, status, message):
        mem_app['params']['symbols'][__symbol]['socket_price'] = None
        print(f"{date_now()}: Закрытие price сокета для символа [{self.header['symbol']}], {status, message}")

    socket = 'wss://stream.binance.com:9443/ws'
    websocket.WebSocketApp(socket,
                           on_open=on_open_price,
                           on_message=on_message_price,
                           on_error=error_price,
                           on_close=close_price,
                           header={'symbol': __symbol}
                           ).run_forever()


# def init_mem_app(traders_list):
#     for trader in traders_list:
#         if trader[0] not in mem_app['deals'].keys():
#             mem_app['deals'][trader[0]] = {'symbol': (trader[1], trader[2]),
#                                        'first_order': (trader[3], trader[4], trader[5], [trader[6], trader[7]]),
#                                        'second_order': (trader[8], trader[9], trader[10], [trader[11], trader[12]]),
#                                        'stop_flag': False}
#
#         print(f'{date_now()}: Фиксируем торговую операцию в job_list... '
#               f'{mem_app['deals'][trader[0]]}')
#
#         # Здесь, сразу, запустим поток на открытие сокета прайс-листа...
#         price_thread = Thread(target=price_socket, args=[mem_app['deals'][trader[0]]['symbol'][1]])
#         price_thread.start()


if __name__ == '__main__':
    while True:
        # Запросим информацию о всех открытых торговых операциях
        traders = get_trader_protokol('BINANCE:timeless', tuple(mem_app['deals'].keys()))

        if traders == 'err':
            sys.exit()

        if not traders:
            time.sleep(100000)
            continue

        for trader in traders:
            if trader[0] not in mem_app['deals'].keys():
                mem_app['deals'][trader[0]] = {'symbol': (trader[1], trader[2]),
                                               'first_order': [trader[3], trader[4], trader[5], [trader[6], trader[7]]],
                                               'second_order': [trader[8], trader[9], trader[10],
                                                                [trader[11], trader[12]]],
                                               'stop_flag': False}

                print(f'{date_now()}: Фиксируем торговую операцию в job_list... '
                      f'{mem_app['deals'][trader[0]]['symbol']}')

                trader_thread = Thread(target=trade_job_thread, args=[trader[0], ])
                trader_thread.start()
        time.sleep(10000)

        # # Здесь, сразу, запустим поток на открытие сокета прайс-листа...
        # price_thread = Thread(target=price_socket, args=[mem_app['deals'][trader[0]]['symbol'][1]])
        # price_thread.start()

        # if not mem_app['deals'][39]['first_order'][3][1]:
        #     print(f'{date_now()}: Фиксируем "открытие" сначала первой торговой сделки... '
        #           f'{mem_app['deals'][39]['first_order']}')
        # else:
        #     print(f'{date_now()}: Фиксируем "наблюдение" второй торговой сделки... '
        #           f'{mem_app['deals'][39]['first_order']}')

        # mem_app['deals']['symbol'] = trader
        # mem_app['deals']['first_order'] = trader
        # mem_app['deals']['second_order'] = trader
        #
        # if trader not in mem_app['deals'].keys():
        #     first_order = mem_app['deals']['first_order']
        #
        #     if not first_order['status']:
        #         # Сразу поставим первую сделку.
        #         first_deal_thread = Thread(target=set_0_order, args=[trader, ])
        #         first_deal_thread.start()
        #
        #     second_order = mem_app['deals']['second_order']
        #     symbol = None
        #
        #     # Откроем сокет... и будем ждать прайс --> в on_message - запустим второй ордер
        #     print(
        #         f'{date_now()}: Первая сделка завершена, начинаем наблюдение прайса и совершаем вторую торговую '
        #         f'сделку... {trader}')
        #     symbol_socket = Thread(target=price_socket, args=[mem_app['deals']['symbol'], ])
        #     symbol_socket.start()
        time.sleep(10000)
