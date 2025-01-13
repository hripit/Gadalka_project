from pg_base.connection_pg import get_data


def get_all_schema():
    select = '''--Получим информацию о доступных схемах:
                    SELECT schema_name FROM information_schema.schemata;'''
    return get_data(select)


def get_symbols_data(schema):
    select = f"""--Запросим информацию о символах для {schema}
                    SELECT 
	                    TRIM(symbol_name) 
	                    FROM "{schema}".symbols
	                ORDER BY id_symbol ASC; """

    return get_data(select)
