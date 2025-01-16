from uti import date_now, dtime_range
from time import perf_counter
from pg_base.select_pg import get_all_schema, get_symbols_data, get_available_periods
from termcolor import colored
from copy import deepcopy

from binance_job import Lets_start_job

params = dict()


def get_prices():
    print(colored(f"{date_now()}: Script for requesting historical information about prices on trading platforms"
                  f" [by list]."), 'green')

    # Разметим память...
    init()

    Lets_start_job(params)

    # Для каждой схемы и символа запросим имеющуюся информациею в базе, каждая схема обрабатывается в отдельном потоке.
    # update_data(params)


def init():
    template_dict = dict()
    template_dict['period'] = list()
    template_dict['job_times'] = list()

    schemas = get_all_schema()
    for data in schemas:
        if data[0].find('timeless') != -1:
            symbols = get_symbols_data(data[0])
            if not symbols:
                continue

            for symbol in symbols:
                params[data[0]] = {symbol: deepcopy(template_dict)}

