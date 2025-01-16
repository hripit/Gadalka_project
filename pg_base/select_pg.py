import io
from pg_base.connection_pg import get_data, load_dataframe_with_copy


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


def get_open_times(schema, symbol_id):
    select = f"""-- Запросим имеющиеся даты_время по символу 
                    SELECT  
                        open_time	
                    FROM "{schema}".kline_data
                    WHERE
                        symbol_id = {symbol_id}

                    ORDER BY open_time ASC """

    return get_data(select)


def get_available_periods(schema, symbol_id):
    select = f"""-- Запросим минимальную и максимальную дату для исторических данных
                    SELECT  MIN(open_time), date_trunc('minute', now() at time zone ('utc'))
                    FROM "{schema}".kline_data
                    WHERE symbol_id={symbol_id}
    """
    return get_data(select)


def set_frame_to_DB(kline_data):

    # Convert the DataFrame to a CSV file-like object
    csv_buffer = io.StringIO()
    csv = None
    kline_data.to_csv(csv_buffer, index=False, header=False, sep=';')

    csv_buffer.seek(0)

    return load_dataframe_with_copy(csv_buffer)
