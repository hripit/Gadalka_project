import time
from decimal import Decimal, ROUND_DOWN, InvalidOperation

from fontTools.misc.cython import returns

from interface.app_param import mem_app


def ensure_decimal(variable):
    """
    Проверяет тип переменной и преобразует её в Decimal, если это необходимо.

    :param variable: Переменная для проверки и возможного преобразования.
    :return: Объект типа Decimal.
    """
    if not isinstance(variable, Decimal):
        try:
            # Преобразуем переменную в Decimal
            variable = Decimal(variable)
        except (ValueError, InvalidOperation) as e:
            variable = None
    return variable


def normalize_qty(qty_in, min_qty):
    qty_in_out = ensure_decimal(qty_in)
    min_qty_out = ensure_decimal(min_qty)

    if qty_in_out and min_qty_out:
        return qty_in_out.quantize(min_qty_out, rounding=ROUND_DOWN)
    else:
        # print('Беда здесь, нужно внимание -> ', qty_in, min_qty)
        return qty_in_out


def get_order_price(price_data, side, min_price):
    price = 0

    price_ask = Decimal(price_data['asks'][0][0])
    price_bids = Decimal(price_data['bids'][0][0])

    variance = price_ask - price_bids

    if side == 'BUY':
        if variance > min_price:
            price = price_bids + min_price
        else:
            price = price_ask

    elif side == 'SELL':
        if variance > min_price:
            price = price_ask - min_price
        else:
            price = price_bids

    return normalize_qty(price, min_price)


def calculate_order(pocket, base_asset, price, side, fee, minis, quote_asset):
    """
    На вход подается
    :param quote_asset:
    :param pocket: (Количество, монета)
    :param base_asset: Базовая монета
    :param price: Цена
    :param side: Сторона сделки
    :param fee: Комиссия
    :param minis: Параметры для округления
    :return: (Количество, монета)
    """
    pocket_out = base = quote = qb_fee = pocket_in = 0

    if side == 'BUY':
        if not pocket[1][1] == base_asset:
            pocket_out = normalize_qty(pocket[0], minis['precision'][0])
            #     На вход поступила квотируемая монета, выполним обратный расчет
            base = pocket_out / price
            base = normalize_qty(base, minis['min_qty'][0])

            if base < minis['min_qty'][0]:
                return (0, base_asset), 0, side, (0, base_asset), (0, base_asset), (0, base_asset)

            # Пересчитаем взятый объем
            quote = base * price
            quote = normalize_qty(quote, minis['precision'][0])

            qb_fee = base * fee
            qb_fee = normalize_qty(qb_fee, minis['baseAssetPrecision'])

            pocket_in = base - qb_fee
            pocket_in = normalize_qty(pocket_in, minis['baseAssetPrecision'])

        pocket_out = quote
        return pocket_out, base, price, side, quote, qb_fee, (pocket_in, base_asset)

    if side == 'SELL':
        if pocket[1][1] == base_asset:

            base = normalize_qty(pocket[0], minis['min_qty'][0])

            if base < minis['min_qty'][0]:
                return (0, base_asset), 0, side, (0, base_asset), (0, base_asset), (0, quote_asset)
            #     На вход поступила базовая монета, выполним нормальный расчет
            quote = base * price
            quote = normalize_qty(quote, minis['quoteAssetPrecision'])

            qb_fee = quote * fee
            qb_fee = normalize_qty(qb_fee, minis['quoteAssetPrecision'])

            pocket_in = quote - qb_fee
            pocket_in = normalize_qty(pocket_in, minis['quoteAssetPrecision'])

            pocket_out = base

        return pocket_out, base, price, side, quote, qb_fee, (pocket_in, quote_asset)


def profit_deal(min_profit, pocket, base_asset, side, fee_, minis):
    pocket_out = base = price = quote = qb_fee = pocket_in = 0

    if side == 'SELL':
        if pocket[1] == base_asset:
            base = normalize_qty(pocket[0], minis['min_qty'][0])

            price = min_profit[0] / base
            price = normalize_qty(price, minis['min_price'][0])

            quote = price * base
            quote = normalize_qty(quote, minis['precision'][0])

            qb_fee = quote * fee_

            pocket_in = quote - qb_fee
            pocket_in = normalize_qty(pocket_in, minis['quoteAssetPrecision'])

            while pocket_in < min_profit[0]:
                price = price + minis['min_price'][0]
                price = normalize_qty(price, minis['min_price'][0])

                quote = price * base
                quote = normalize_qty(quote, minis['precision'][0])

                qb_fee = quote * fee_
                pocket_in = quote - qb_fee
                pocket_in = normalize_qty(pocket_in, minis['quoteAssetPrecision'])

            pocket_out = base

    if side == 'BUY':
        if not pocket[1] == base_asset:
            quote = normalize_qty(pocket[0], minis['precision'])

            price = quote / min_profit[0]
            price = normalize_qty(price, minis['min_price'][0])

            base = quote / price
            base = normalize_qty(base, minis['min_qty'][0])

            qb_fee = base * fee_
            qb_fee = normalize_qty(qb_fee, minis['baseAssetPrecision'])

            pocket_in = base - qb_fee
            pocket_in = normalize_qty(pocket_in, minis['baseAssetPrecision'])

            while pocket_in < min_profit[0]:
                price = price - minis['min_price'][0]

                base = quote / price
                base = normalize_qty(base, minis['min_qty'][0])

                qb_fee = base * fee_
                qb_fee = normalize_qty(qb_fee, minis['baseAssetPrecision'])

                pocket_in = base - qb_fee
                pocket_in = normalize_qty(pocket_in, minis['baseAssetPrecision'])

            quote = price * base
            quote = normalize_qty(quote, minis['precision'][0])

            pocket_out = quote

    return pocket_out, base, price, side, quote, qb_fee, pocket_in


def calculate_deals(pocket, symbol):
    if not normalize_qty(pocket[0], '0.0000000001'):
        # Не будем продолжать расчет ибо пришло говно.
        return None

    fee = Decimal(symbol['fee'])
    margin = normalize_qty(Decimal(symbol['margin']), symbol['MINIS']['baseAssetPrecision'])
    price_data = symbol['socket_price']
    min_price = symbol['MINIS']['min_price'][0]

    # Определим сторону движения
    side = 'SELL' if symbol['baseAsset'] == pocket[1][1] else 'BUY'
    # Определим нужный прайс
    price_in = get_order_price(price_data, side, min_price)

    # Выполним расчет первой сделки, как есть.
    # if not symbol['symbol'] == 'WIFUSDT':
    #     return

    first_order = calculate_order(pocket, symbol['baseAsset'], price_in, side, fee, symbol['MINIS'],
                                  symbol['quoteAsset'])
    symbol['TRADES']['order_1'] = first_order

    side = 'BUY' if symbol['baseAsset'] == pocket[1][1] else 'SELL'
    min_profit = (first_order[0] * (1 + margin), pocket[1][1])

    second_order = profit_deal(min_profit, first_order[6], symbol['baseAsset'], side, fee, symbol['MINIS'])
    symbol['TRADES']['order_2'] = second_order

    symbol['TRADES']['total']['profit'] = (second_order[6] - first_order[0])
    symbol['TRADES']['total']['profit'] = normalize_qty(symbol['TRADES']['total']['profit'], Decimal('0.01'))

    symbol['TRADES']['total']['spread'] = (1 - (min(first_order[2], second_order[2])
                                                / max(first_order[2], second_order[2]))) * 100
    symbol['TRADES']['total']['spread'] = normalize_qty(symbol['TRADES']['total']['spread'], Decimal('0.01'))
