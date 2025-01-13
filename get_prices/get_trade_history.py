from uti import date_now
from time import perf_counter
from pg_base.select_pg import get_all_schema, get_symbols_data

params = dict()


def get_prices():
    start_proc = perf_counter()
    print(f"{date_now()}: Script for requesting historical information about prices on trading platforms [by list].")

    init()

    end_proc = perf_counter()
    print(f"{date_now()}: The script for requesting historical information is complete.\n\t\t\t\t\t"
          f"start_proc: [{start_proc}] :: end_proc: [{end_proc}] :: duration_time: [{end_proc-start_proc}]")


def init():
    schemas = get_all_schema()
    for data in schemas:
        if data[0].find('timeless') != -1:
            symbols = get_symbols_data(data[0])
            if not symbols:
                continue

            for symbol in symbols:
                params[data[0]] = {symbol[0]: dict()}

    print(params)
