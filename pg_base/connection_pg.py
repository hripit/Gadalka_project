import sys
import time

from psycopg import connect, Error
from parameters import PARAMS_DB
from uti import date_now
from time import perf_counter
from termcolor import colored


def open_base_connection():
    try:
        response = connect(user=PARAMS_DB["user"],
                           password=PARAMS_DB["password"],
                           host=PARAMS_DB["host"],
                           port=PARAMS_DB["port"],
                           dbname=PARAMS_DB["dbname"])

    except Error as err:
        print(colored(f"{date_now()}: Хуйня вышла-с open_base_connection(): "
              f"\n\t\t\t\t\t--> текст ошибки: [{err.diag.message_primary}]", 'red'))
        response = None

    return response


def get_data(select):
    start_proc = perf_counter()

    _db_connection = None

    while not _db_connection:
        _db_connection = open_base_connection()
        if not _db_connection:
            time.sleep(1)

    _cursor = _db_connection.cursor()

    try:
        _cursor.execute(select)
        response = _cursor.fetchall()

    except Error as err:
        print(colored(f"{date_now()}: Хуйня вышла-с в запросе: \n\t\t\t\t\t[{select}]"
              f"\n\t\t\t\t\t--> текст ошибки: [{err.diag.message_primary}]", 'red'))
        response = None
        # sys.exit()

    finally:
        _cursor.close()
        _db_connection.close()

    end_proc = perf_counter()
    print(f"{date_now()}: Get pg_data:\n\t\t\t\t\t{select}"
          f"\n\t\t\t\t\tstart_proc: [{start_proc}] "
          f":: end_proc: [{end_proc}] :: duration_time: [{end_proc - start_proc}]")

    return response
