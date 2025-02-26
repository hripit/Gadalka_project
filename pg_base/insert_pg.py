from pg_base.connection_pg import insert_data


def insert_order(pg_id, status_id, price, json_limit_order_1):
    insert = f'''-- Сохраним ордер:
    INSERT INTO "BINANCE:timeless".orders(
	symbol_id, status_id, price, body_json)
	VALUES ({pg_id}, {status_id}, {price}, '{json_limit_order_1}'::JSONB)
	RETURNING order_id;'''

    return insert_data(insert)


def insert_trade_operation(first_id, second_id, symbol_id):
    insert = f'''-- Сохраним торговую операцию:
    INSERT INTO "BINANCE:timeless".trade_operations(
	first_id, second_id, symbol_id)
	VALUES ({first_id}, {second_id}, {symbol_id})
	RETURNING trade_id;'''

    return insert_data(insert)

