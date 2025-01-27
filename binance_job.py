import sys
import time
import pandas as pd
from binance.spot import Spot
from binance.error import ClientError
from uti import date_now, convert_from_timestamp, dtime_range, convert_to_timestamp, repack_list
from termcolor import colored
from time import perf_counter
from threading import Thread
from pg_base.select_pg import get_available_periods, get_open_times, set_frame_to_DB
from json import dumps

# Секция хранения параметров подключения API Binance
PARAMS_BI = {"api_key": None, 'api_secret': None}


def Lets_start_job(params: dict):
    """Точка входа для job, где params содержит:\n
    {[Схема базы данных]:
        {[Символ]: [['period'], ['job_times'], ]}}"""

    start_proc = perf_counter()

    if not params:
        print(colored(f"{date_now()}: Shit is happen : An empty parameter [params] was received at the input, "
                      f"the work will be terminated"), 'red')

    # Убедимся что существует указанная схема базы данных:

    # Для каждого символа откроем отдельный поток на запрос данных.
    job_threads_list = list()
    for schema_key in params.keys():
        for symbol_key in params[schema_key].keys():
            job_thread = Thread(target=kline_data_job, args=[params, schema_key, symbol_key])
            job_threads_list.append(job_thread)

    for job_thread in job_threads_list:
        job_thread.start()
        # time.sleep(1)

    for job_thread in job_threads_list:
        job_thread.join()

    end_proc = perf_counter()
    duration = end_proc - start_proc
    print(colored(f"{date_now()}: The job for requesting historical information is complete.\n\t"
          f" start_proc: [{start_proc}] :: end_proc: [{end_proc}] :: duration_time: [{duration}]", 'magenta'))


def kline_data_job(params: dict, schema: str, symbol: list):
    start_proc = perf_counter()

    params[schema][symbol]['period'] = combine_period(schema, symbol)

    params[schema][symbol]['job_times'] = first_rule(params, schema, symbol)

    if not params[schema][symbol]['job_times'].empty:
        # Если нашли незаполненные периоды, запускаем job для загрузки данных торговой площадки.
        print(f"{date_now()}: Attention! Found missing data [{symbol[1]}] for periods:"
              f" [{params[schema][symbol]['period'][0]}] :: "
              f"[{params[schema][symbol]['period'][1]}]. "
              f"The data will be reloaded ...soon.")

        params[schema][symbol]['job_times'] = download_data(params, schema, symbol)

        # Применим фрейм в БД
        set_frame_to_DB(schema, params[schema][symbol]['job_times'])
        params[schema][symbol]['job_times'] = None

    end_proc = perf_counter()
    duration = end_proc - start_proc
    print(colored(f"{date_now()}: Thread for schema [{schema}] :: symbol: [{symbol}] is complete.\n\t"
                  f" start_proc: [{start_proc}] :: end_proc: [{end_proc}] :: duration_time: [{duration}]", 'magenta'))


def combine_period(schema, symbol):

    period = get_available_periods(schema, symbol[0])
    if not period[0][0]:
        period = dtime_range()
    else:
        period = [period[0][0], period[0][1]]

    return period


def first_rule(params, schema, symbol):
    """
    Проверим иметься ли информация для заданного периода в базе данных.
    :return [empty_times] Список значений open_time. Означает что в списке дат,
    информация о прайсе отсутствует в БД.
    """
    period = params[schema][symbol]['period']
    open_times_data = get_open_times(schema, symbol[0])

    open_times_data = pd.DataFrame(data=open_times_data, columns=['date_time'], dtype='datetime64[ns]')
    open_times_data['date_time_concat'] = open_times_data['date_time']

    pd_data_range = pd.date_range(start=period[0], end=period[1], freq='min')
    pd_data_range = pd.DataFrame(data=pd_data_range, columns=['date_time'])

    empty_times = pd_data_range.merge(open_times_data, on='date_time', how='left')
    empty_times = empty_times[empty_times['date_time_concat'].isnull()]
    empty_times = empty_times.drop('date_time_concat', axis=1)

    return empty_times


def download_data(params, schema, symbol):
    empty_frame = params[schema][symbol]['job_times']

    # Запросим пакет данных у биржи о прайсе, лимит выдачи 1000 записей.
    ind = 0
    length_period = empty_frame.shape[0]
    kline_data_list = list()

    while ind < length_period:
        start_date = empty_frame.iloc[ind]['date_time']

        ind = ind + 998
        ind = min(ind, length_period - 1)

        end_date = empty_frame.iloc[ind]['date_time']
        kline_data_list.append(kline_data_1m(symbol[1],
                                             convert_to_timestamp(start_date), convert_to_timestamp(end_date)))

        ind += 1
    kline_data_list = repack_list(kline_data_list)

    kline_frame = pd.Series(data=kline_data_list).to_frame(name='json')
    kline_frame['date_time'] = kline_frame.apply(lambda x: convert_from_timestamp(x['json'][0]), axis=1)

    empty_frame = empty_frame.merge(kline_frame, on='date_time')
    # Распакуем json до нужных полей во фрейм
    # [
    #   [
    #     1499040000000,      // Kline open time    0
    #     "0.01634790",       // Open price         1
    #     "0.80000000",       // High price         2
    #     "0.01575800",       // Low price          3
    #     "0.01577100",       // Close price        4
    #     "148976.11427815",  // Volume             5
    #     1499644799999,      // Kline Close time   6
    #     "2434.19055334",    // Quote asset volume 7
    #     308,                // Number of trades   8
    #     "1756.87402397",    // Taker buy base asset volume    9
    #     "28.46694368",      // Taker buy quote asset volume   10
    #     "0"                 // Unused field, ignore.          11
    #   ]
    # ]
    empty_frame['high_price'] = [v[2] for v in empty_frame['json'].values]
    empty_frame['low_price'] = [v[3] for v in empty_frame['json'].values]
    empty_frame['volume'] = [v[5] for v in empty_frame['json'].values]
    empty_frame['symbol_id'] = symbol[0]
    empty_frame['json'] = [dumps(v) for v in empty_frame['json'].values]

    # empty_frame = empty_frame.drop('json', axis=1)

    params[schema][symbol]['job_times'] = empty_frame

    return empty_frame


def get_connection_binance():
    connection = None
    try:
        connection = Spot(PARAMS_BI["api_key"], PARAMS_BI["api_secret"])
    except ClientError as error:
        print("{}: Shit came out : get_connection_binance(): "
              "{}, error code: {}, error message: {}".format(date_now,
                                                             error.status_code, error.error_code, error.error_message))

    return connection


def kline_data_1m(symbol: str, start_time: int, end_time: int):
    connection = response = None

    while not connection:
        connection = get_connection_binance()
        if not connection:
            time.sleep(1)

    try:
        response = connection.klines(symbol=symbol, interval='1m', startTime=start_time, endTime=end_time, limit=1000)

    except ClientError as error:
        print("{}: Shit came out : kline_data_1m(symbol: str, start_time: int, end_time: int): {}, error code: {}, "
              "error message: {}".format(date_now, error.status_code, error.error_code, error.error_message))

        sys.exit()

    if response:
        print(colored(f"{date_now()}: Data received: [{symbol}] ... "
                      f"[{convert_from_timestamp(response[0][0])}] ... "
                      f"[# same kline data ***********] ... length is [{len(response)}] times", 'yellow'))
    else:
        print(colored(f"{date_now()}: No data available, "
                      f"reason needs to be clarified: [{symbol}], "
                      f"[{convert_from_timestamp(start_time)}] ... [{None}] ", 'cyan'))

    return response
###
