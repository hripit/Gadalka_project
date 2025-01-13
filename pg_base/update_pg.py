
def open_base_connection():
    try:
        response = psycopg2.connect(user=PARAMS_DB["user"],
                                    password=PARAMS_DB["password"],
                                    host=PARAMS_DB["host"],
                                    port=PARAMS_DB["port"],
                                    dbname=PARAMS_DB["dbname"])

    except db_errors as error:
        print(f"{date_now()}: Хуйня вышла-с open_base_connection(): "
              f"{error.status_code}, error code: {error.error_code}, error message: {error.error_message}")
        response = False

    return response