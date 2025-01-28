import io
from pg_base.connection_pg import get_data, apply_dataframe_with_copy


def get_all_schema():
    select = '''-- Получим информацию о доступных схемах:
                    SELECT schema_name FROM information_schema.schemata;'''
    return get_data(select)


def get_symbols_data(schema):
    select = f"""-- Запросим информацию о символах для {schema}
                    SELECT 
                        symbol_id
	                    , TRIM(symbol) 
	                    FROM "{schema}".symbols_data"""

    return get_data(select)


def get_open_times(schema, symbol_id):
    select = f"""-- Запросим имеющиеся даты_время по символу 
                    SELECT  
                        open_time	
                    FROM "{schema}".kline_data
                    WHERE
                        symbol_id = {symbol_id};"""

    return get_data(select)


def get_available_periods(schema, symbol_id):
    select = f"""-- Запросим минимальную и максимальную дату для исторических данных
                    SELECT  MIN(open_time), date_trunc('minute', now() at time zone ('utc'))
                    FROM "{schema}".kline_data
                    WHERE symbol_id={symbol_id};"""

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
