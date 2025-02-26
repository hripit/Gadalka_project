# Стандартная библиотека Python
from time import perf_counter
from threading import Thread

# Внешние библиотеки
import pandas as pd
from binance.error import ClientError
from binance.spot import Spot
from fontTools.misc.cython import returns
from termcolor import colored

# Локальные модули
from pg_base.select_pg import get_available_periods, get_open_times, set_frame_to_DB
from uti import convert_from_timestamp, convert_to_timestamp, date_now, dtime_range, repack_list

# JSON для работы с данными
from json import dumps

# Секция хранения параметров подключения API Binance
PARAMS_BI = {"api_key": None, 'api_secret': None}

# Кэширование подключения к Binance
binance_connection = None


def Lets_start_job(params: dict):
    """Точка входа для job."""
    start_proc = perf_counter()
    if not params:
        print(colored(f"{date_now()}: Ошибка: Получен пустой параметр [params]. Работа будет прекращена.", 'red'))
        return

    # Создаем потоки для каждого символа
    job_threads = []
    for schema in params.keys():
        for symbol in params[schema].keys():
            thread = Thread(target=kline_data_job, args=[params, schema, symbol])
            job_threads.append(thread)
            thread.start()

    # Ждем завершения всех потоков
    for thread in job_threads:
        thread.join()

    end_proc = perf_counter()
    duration = end_proc - start_proc
    print(colored(f"{date_now()}: Запрос исторической информации завершен. "
                  f"Время выполнения: {duration:.2f} секунд", 'magenta'))


# def kline_data_job(params: dict, schema: str, symbol: list):
#     """Обработка данных для конкретного символа."""
#     start_proc = perf_counter()
#
#     try:
#         # Получаем период и временные метки
#         params[schema][symbol]['period'] = combine_period(schema, symbol)
#         params[schema][symbol]['job_times'] = first_rule(params, schema, symbol)
#
#         if not params[schema][symbol]['job_times'].empty:
#             print(colored(f"{date_now()}: Недостающие данные [{symbol[1]}] за период: "
#                           f"[{params[schema][symbol]['period'][0]}] - [{params[schema][symbol]['period'][1]}]. "
#                           f"Начинаем загрузку...", 'yellow'))
#
#             # Загружаем данные и сохраняем в БД
#             params[schema][symbol]['job_times'] = download_data(params, schema, symbol)
#             set_frame_to_DB(schema, params[schema][symbol]['job_times'])
#
#     except Exception as e:
#         print(colored(f"{date_now()}: Ошибка при обработке символа [{symbol[1]}]: {e}", 'red'))
#
#     finally:
#         end_proc = perf_counter()
#         duration = end_proc - start_proc
#         print(colored(f"{date_now()}: Поток для схемы [{schema}] :: символ [{symbol[1]}] завершен. "
#                       f"Время выполнения: {duration:.2f} секунд", 'magenta'))

def kline_data_job(params: dict, schema: str, symbol: list):
    """Обработка данных для конкретного символа."""
    start_proc = perf_counter()

    # Получаем период и временные метки
    params[schema][symbol]['period'] = combine_period(schema, symbol)
    params[schema][symbol]['job_times'] = first_rule(params, schema, symbol)

    if not params[schema][symbol]['job_times'].empty:
        print(colored(f"{date_now()}: Недостающие данные [{symbol[1]}] за период: "
                      f"[{params[schema][symbol]['period'][0]}] - [{params[schema][symbol]['period'][1]}]. "
                      f"записей: [{len(params[schema][symbol]['job_times'])}] "
                      f"Начинаем загрузку...", 'yellow'))

        # Загружаем данные и сохраняем в БД
        params[schema][symbol]['job_times'] = download_data(params, schema, symbol)
        set_frame_to_DB(schema, params[schema][symbol]['job_times'])

    end_proc = perf_counter()
    duration = end_proc - start_proc
    print(colored(f"{date_now()}: Поток для схемы [{schema}] :: символ [{symbol[1]}] завершен. "
                  f"Время выполнения: {duration:.2f} секунд", 'magenta'))


def combine_period(schema, symbol):
    """Составляет период для запроса данных."""
    period = get_available_periods(schema, symbol[0])
    return dtime_range() if not period[0][0] else [period[0][0], period[0][1]]


def first_rule(params, schema, symbol):
    """
    Проверим иметься ли информация для заданного периода в базе данных.
    :return [empty_times] Список значений open_time. Означает что в списке дат,
    информация о прайсе отсутствует в БД.
    """
    period = params[schema][symbol]['period']
    open_times_data = get_open_times(schema, symbol[0])

    open_times_data = pd.DataFrame(data=open_times_data, columns=['open_time'], dtype='datetime64[ns]')

    pd_data_range = pd.date_range(start=period[0], end=period[1], freq='min')
    pd_data_range = pd.DataFrame(data=pd_data_range, columns=['open_time'])

    # Находим пропущенные временные метки
    empty_times = pd_data_range.merge(open_times_data, on='open_time', how='left', indicator=True)
    empty_times = empty_times[empty_times['_merge'] == 'left_only'].drop(columns=['_merge'])

    return empty_times


def download_data(params, schema, symbol):
    """Загружает недостающие данные с Binance."""
    empty_frame = params[schema][symbol]['job_times']

    # Запросим пакет данных у биржи о прайсе, лимит выдачи 1000 записей.
    ind = 0
    length_period = empty_frame.shape[0]
    kline_data_list = []

    while ind < length_period:
        start_date = empty_frame.iloc[ind]['open_time']
        ind = ind + 999
        ind = min(ind, length_period)
        end_date = empty_frame.iloc[ind - 1]['open_time']

        kline_data_list.append(kline_data_1m(symbol[1],
                                             convert_to_timestamp(start_date), convert_to_timestamp(end_date)))

        ind += 1

    kline_data_list = repack_list(kline_data_list)

    kline_frame = pd.Series(data=kline_data_list).to_frame(name='kline_json')
    kline_frame['open_time'] = kline_frame.apply(lambda x: convert_from_timestamp(x['kline_json'][0]), axis=1)

    empty_frame = empty_frame.merge(kline_frame, on='open_time')
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
    empty_frame['price_hi'] = [v[2] for v in empty_frame['kline_json'].values]
    empty_frame['price_low'] = [v[3] for v in empty_frame['kline_json'].values]
    empty_frame['volume'] = [v[5] for v in empty_frame['kline_json'].values]
    empty_frame['symbol_id'] = symbol[0]
    empty_frame['kline_json'] = [dumps(v) for v in empty_frame['kline_json'].values]

    # empty_frame = empty_frame.drop('json', axis=1)

    params[schema][symbol]['job_times'] = empty_frame

    return empty_frame


def get_connection_binance():
    """Получает подключение к Binance с кэшированием."""
    global binance_connection
    if not binance_connection:
        try:
            binance_connection = Spot(PARAMS_BI["api_key"], PARAMS_BI["api_secret"])
        except ClientError as error:
            print(colored(f"{date_now()}: Ошибка подключения к Binance: {error}", 'red'))
    return binance_connection


def kline_data_1m(symbol: str, start_time: int, end_time: int):
    """Запрашивает данные о свечах (klines) с Binance."""
    connection = get_connection_binance()
    if not connection:
        print(colored(f"{date_now()}: Подключение к Binance отсутствует.", 'red'))
        return []

    try:
        response = connection.klines(symbol=symbol, interval='1m', startTime=start_time, endTime=end_time, limit=1000)
        if response:
            print(colored(f"{date_now()}: Получены данные для [{symbol}] с [{convert_from_timestamp(response[0][0])}] "
                          f"по [{convert_from_timestamp(response[-1][0])}]", 'green'))
        else:
            print(colored(f"{date_now()}: Для [{symbol}] данных не найдено.", 'cyan'))
        return response
    except ClientError as error:
        print(colored(f"{date_now()}: Ошибка при запросе данных для [{symbol}]: {error}", 'red'))
        return []
