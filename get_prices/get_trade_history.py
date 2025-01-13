from uti import date_now, dtime_1year_range
from time import perf_counter
from pg_base.select_pg import get_all_schema, get_symbols_data
from termcolor import colored
from copy import deepcopy

params = dict()


def get_prices():
    start_proc = perf_counter()
    print(colored(f"{date_now()}: Script for requesting historical information about prices on trading platforms [by list]."), 'green')

    # Разметим память...
    init()

    # Для каждой схемы и символа запросим имеющуюся информациею в базе
    for key_schema, value_schema in params.items():
        for key_symbol, value_symbol in value_schema.items():
            print(key_schema, key_symbol)

    end_proc = perf_counter()
    print(f"{date_now()}: The script for requesting historical information is complete.\n\t\t\t\t\t"
          f"start_proc: [{start_proc}] :: end_proc: [{end_proc}] :: duration_time: [{end_proc-start_proc}]")


def init():
    template_dict = dict()
    template_dict['period'] = dtime_1year_range(None)
    template_dict['kline_data'] = list()

    schemas = get_all_schema()
    for data in schemas:
        if data[0].find('timeless') != -1:
            symbols = get_symbols_data(data[0])
            if not symbols:
                continue

            for symbol in symbols:
                params[data[0]] = {symbol: deepcopy(template_dict)}

    print(params)

