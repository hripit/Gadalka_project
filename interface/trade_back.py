import sys
from threading import Thread

from termcolor import colored

from interface.app_param import message_md, mem_app
from uti import date_now
from json import dumps, loads
from pg_base.insert_pg import insert_order, insert_trade_operation


def json_order(symbol: str, order: dict):
    limit_order = {
        "symbol": symbol,
        "strategyId": '0804',
        "timeInForce": "GTC",
        "recvWindow": "5000",
        "side": order[3],
        "type": 'LIMIT',
        "price": str(order[2]),
        "quantity": str(order[1])
    }

    return dumps(limit_order)


def trade_thread(symbol: str):
    pg_id = mem_app['params']['symbols'][symbol]['PG_ID']
    status_id = 0

    order_1 = mem_app['params']['symbols'][symbol]['TRADES']['order_1']
    order_2 = mem_app['params']['symbols'][symbol]['TRADES']['order_2']

    if not (order_1 or order_2):
        return

    # 1. Сформируем корректные json'ы
    json_limit_order_1 = json_order(symbol, order_1)
    json_limit_order_2 = json_order(symbol, order_2)

    # 2. Запишем торговую сделку в базу данных
    order_1_id = insert_order(pg_id, status_id, order_1[2], json_limit_order_1)
    if not order_1_id:
        colored(print(date_now(), 'Данные первого ордера не легли в базу --> ', order_1), 'red')
        sys.exit()

    order_2_id = insert_order(pg_id, status_id, order_2[2], json_limit_order_2)
    if not order_2_id:
        colored(print(date_now(), 'Данные второго ордера не легли в базу --> ', order_2), 'red')
        sys.exit()

    trade_id = insert_trade_operation(order_1_id[0], order_2_id[0], pg_id)
    if not trade_id:
        colored(print(date_now(), 'Данные торговой операции не легли в базу --> ', order_1[0], order_2[0]), 'red')
        sys.exit()

    if symbol == 'WIFUSDT':
        print(date_now(), json_limit_order_1, ' --> \n', json_limit_order_2)


def Go_trade():
    for symbol in mem_app['params']['symbols']:
        price_thread = Thread(target=trade_thread, args=(symbol,))
        price_thread.start()
