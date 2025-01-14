from pg_base.connection_pg import get_data


def get_all_schema():
    select = '''-- Получим информацию о доступных схемах:
                    SELECT schema_name FROM information_schema.schemata;'''
    return get_data(select)


def get_symbols_data(schema):
    select = f"""-- Запросим информацию о символах для {schema}
                    SELECT 
                        symbol_id
	                    , TRIM(symbol_name) 
	                    FROM "{schema}".symbols
	                ORDER BY symbol_id ASC; """

    return get_data(select)


def get_open_times(schema, symbol_id, period):
    select = f"""-- Запросим имеющиеся даты_время по символу 
                    SELECT  
                        open_time	
                    FROM "{schema}".kline_data
                    WHERE
                        symbol_id_id = {symbol_id}
                        AND open_time BETWEEN ('{period[0]}'::timestamp) and ('{period[1]}'::timestamp)
                    ORDER BY open_time ASC """

    return get_data(select)


def get_available_periods(schema, symbol_id):
    select = f"""-- Запросим минимальную и максимальную дату для исторических данных
                    SELECT MIN(open_time), MAX(open_time) 
                    FROM "{schema}".kline_data
                    WHERE symbol_id_id={symbol_id}
    """
    return get_data(select)
