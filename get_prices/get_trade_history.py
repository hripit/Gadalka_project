from uti import date_now, dtime_range
from time import perf_counter
from pg_base.select_pg import get_all_schema, get_symbols_data, get_available_periods
from termcolor import colored
from copy import deepcopy
from threads_job import check_available_data

params = dict()


def get_prices():
    start_proc = perf_counter()
    print(colored(f"{date_now()}: Script for requesting historical information about prices on trading platforms"
                  f" [by list]."), 'green')

    # Разметим память...
    init()

    # Для каждой схемы и символа запросим имеющуюся информациею в базе, каждая схема обрабатывается в отдельном потоке.
    check_available_data(params)

    end_proc = perf_counter()
    print(f"{date_now()}: The script for requesting historical information is complete.\n\t\t\t\t\t"
          f" start_proc: [{start_proc}] :: end_proc: [{end_proc}] :: duration_time: [{end_proc-start_proc}]")


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
                periods = get_available_periods(data[0], symbol[0])
                if not periods:
                    periods = dtime_range()

                template_dict['period'] = periods[0]

                params[data[0]] = {symbol: deepcopy(template_dict)}
