import time

from uti import date_now
from pg_base.select_pg import get_all_schema, get_symbols_data
from termcolor import colored
from copy import deepcopy

from binance_job import Lets_start_job

params = dict()


def get_prices():
    # Разметим память...
    print(colored(f"{date_now()}: Script for requesting historical information "
                  f"about prices on trading platforms [by list]", 'magenta'))

    init()

    while True:
        print(colored(f"{date_now()}: Script for requesting historical information "
                      f"about prices on trading platforms [by list]", 'magenta'))

        Lets_start_job(params)
        time.sleep(60)


    # Для каждой схемы и символа запросим имеющуюся информациею в базе, каждая схема обрабатывается в отдельном потоке.
    # update_data(params)


def init():
    template_dict = dict()
    template_dict['period'] = list()
    template_dict['job_times'] = list()
    temp_symbols = dict()

    schemas = get_all_schema()
    for data in schemas:
        if data[0].find('timeless') != -1:
            symbols = get_symbols_data(data[0])
            if not symbols:
                continue

            for symbol in symbols:
                temp_symbols[symbol] = deepcopy(template_dict)

            params[data[0]] = temp_symbols
