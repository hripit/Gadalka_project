import io
from pg_base.connection_pg import get_data, apply_dataframe_with_copy, open_base_connection
import pandas as pd
from sqlalchemy import create_engine
from parameters import PARAMS_DB
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from termcolor import colored
from uti import date_now

DB_ENGINE = create_engine(
    f'postgresql://{PARAMS_DB["user"]}:{PARAMS_DB["password"]}@{PARAMS_DB["host"]}:{PARAMS_DB["port"]}/{PARAMS_DB["dbname"]}')


def get_all_schema():
    select = '''-- Получим информацию о доступных схемах: 
    SELECT schema_name FROM information_schema.schemata;'''
    return get_data(select)


def get_symbols_data(schema):
    select = f"""-- Запросим информацию о символах для {schema}
                    SELECT symbol_id, TRIM(symbol) FROM "{schema}".symbols_data"""

    return get_data(select)


def get_open_times(schema, symbol_id):
    select = f"""-- Запросим имеющиеся даты_время по символу 
                    SELECT open_time FROM "{schema}".kline_data WHERE symbol_id = {symbol_id};"""

    return get_data(select)


def get_available_periods(schema, symbol_id):
    select = f"""-- Запросим минимальную и максимальную дату для исторических данных
                    SELECT  MIN(open_time), date_trunc('minute', now() at time zone ('utc'))
                    FROM "{schema}".kline_data WHERE symbol_id={symbol_id};"""

    return get_data(select)


def set_frame_to_DB(schema, kline_data):
    # Convert the DataFrame to a CSV file-like object
    csv_buffer = io.StringIO()
    kline_data.to_csv(csv_buffer, index=False, header=False, sep=';')

    select = f"""-- Применим информацию из фрейма в базу данных.
                    COPY \"{schema}\".kline_data 
                        (open_time, kline_json,  price_hi, price_low, volume, symbol_id)
                    FROM STDIN
                    WITH CSV DELIMITER as ';';"""

    csv_buffer.seek(0)

    return apply_dataframe_with_copy(select, csv_buffer)


def select_layers(schema):
    select = f'''--Запросим расчетные слои
    SELECT 
		md.layer_id
		, md.base_asset 
		, md.margin 
		, md.symbol_id, TRIM(sy.symbol)
		, md.coin_id, TRIM(co.coin)
		, md.default

	FROM "{schema}".model_layer md
	LEFT JOIN "{schema}".symbols_data sy on sy.symbol_id = md.symbol_id
	LEFT JOIN "{schema}".coin_data co on co.coin_id = md.coin_id
	WHERE md.state = True
	ORDER BY md.default desc, md.layer_id;'''

    return get_data(select)


def get_coin(schema, coin):
    select = f'''--Инициализируем монету
        SELECT coin_id, TRIM(coin) FROM "{schema}".coin_data WHERE coin = '{coin}';'''

    return get_data(select)


def get_symbols(schema):
    select = f'''--Инициализируем символы
        SELECT symbol_id, TRIM(symbol) FROM "{schema}".symbols_data;'''

    return get_data(select)


def get_trader_protokol(schema, not_in):
    if not_in:
        if len(not_in) == 1:
            not_in = (not_in[0], 0)
        not_in = f'and toper.trade_id not in {not_in}'
    else:
        not_in = ''

    select = f'''--Инициализация торгового протокола
    SELECT 
		toper.trade_id
		, toper.symbol_id
		, TRIM(symbol.symbol)

		, orde_first.order_id
		, orde_first.body_json
		, orde_first.platform_uid
		, first_st.status_id
		, TRIM(first_st.status_name)

		, orde_second.order_id
		, orde_second.body_json
		, orde_second.platform_uid
		, second_st.status_id
		, TRIM(second_st.status_name)		

	FROM "{schema}".trade_operations as toper

    LEFT JOIN "{schema}".orders as orde_first on toper.first_id = orde_first.order_id
    LEFT JOIN  "{schema}".orders_status as first_st on first_st.status_id = orde_first.status_id

    LEFT JOIN "{schema}".orders as orde_second on toper.second_id = orde_second.order_id
    LEFT JOIN  "{schema}".orders_status as second_st on second_st.status_id = orde_second.status_id

    LEFT JOIN "{schema}".symbols_data as symbol on toper.symbol_id = symbol.symbol_id

    WHERE (first_st.status_id not in (2, 3, 99) or second_st.status_id not in (2, 3, 99) ) 
        {not_in}
        order by toper.trade_id
    LIMIT 1
    ;'''

    return get_data(select)


def get_price_by_week(week, ind_week):
    # Создаем engine для подключения к PostgreSQL
    engine = create_engine(
        f'postgresql://{PARAMS_DB["user"]}:{PARAMS_DB["password"]}@{PARAMS_DB["host"]}:{PARAMS_DB["port"]}/{PARAMS_DB["dbname"]}')

    select = f'''WITH params AS (
        SELECT 
            DATE_TRUNC('day', NOW()) - INTERVAL '{week} week' AS start_of_week,
            (DATE_TRUNC('day', NOW()) - INTERVAL '{week}  week') 
            + INTERVAL '1 day' - INTERVAL '1 millisecond' AS week_of_end)
        SELECT 
            kd_today.open_time AS open_time,
            kd_today.price_low AS {ind_week}
        FROM "BINANCE:timeless".kline_data kd_today
        CROSS JOIN params
        LEFT JOIN "BINANCE:timeless".symbols_data sy ON kd_today.symbol_id = sy.symbol_id
        WHERE 
            --DATE_PART('dow', kd_today.open_time) = DATE_PART('dow', NOW()) 
            --AND 
            kd_today.open_time BETWEEN params.start_of_week AND params.week_of_end
            AND sy.symbol_id = 3
        ORDER BY kd_today.open_time;'''

    df = pd.read_sql(select, engine, parse_dates=['open_time'])

    return df


def get_line_by_week(start_dt, end_dt, coin, symbol, margin, base_asset):
    """
    Запрашивает данные из PostgreSQL за указанный период.

    :param start_dt: Начальная дата (в формате 'YYYY-MM-DD HH:MM:SS').
    :param end_dt: Конечная дата (в формате 'YYYY-MM-DD HH:MM:SS').
    :param coin: Название монеты.
    :param symbol: Название торговой пары.
    :param margin: Значение маржи.
    :param base_asset: Базовый актив.
    :return: DataFrame с результатами запроса.
    """

    try:
        query = text("""
            SELECT
                ht.open_time AS open_time,
                tm.time_left AS time_left
            FROM "BINANCE:timeless".hst_trade ht
            LEFT JOIN "BINANCE:timeless".trade_model tm ON ht.sid = tm.sid_start
            LEFT JOIN "BINANCE:timeless".hst_trade target ON target.sid = tm.sid_target
            WHERE
                tm.coin = :coin
                AND ht.symbol = :symbol
                AND tm.margin = :margin
                AND tm.base_asset = :base_asset
                AND ht.open_time BETWEEN :start_dt AND :end_dt
                AND tm.profit > 0;
        """)

        # Выполнение запроса с использованием параметров
        with DB_ENGINE.connect() as connection:
            df = pd.read_sql_query(query, connection, params={
                "coin": coin,
                "symbol": symbol,
                "margin": margin,
                "base_asset": base_asset,
                "start_dt": start_dt,  # Передаем параметры как строки
                "end_dt": end_dt  # Передаем параметры как строки
            }, parse_dates=['open_time'])

            return df

    except Exception as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
