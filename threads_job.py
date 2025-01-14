import datetime
import random
import threading
from pg_base.select_pg import get_open_times
from binance_job import kline_data_1m
import pandas as pd
from uti import date_now, convert_to_timestamp


def kline_data(t_args):
    params = t_args[0]
    schema = t_args[1]
    symbol = t_args[2]
    period = t_args[3]

    def first_rule():
        """
        Проверим иметься ли информация для заданного периода в базе данных.
        :Заполним [params] Список значений open_time. Означает что на список дат,
        информация о прайсе отсутствует в БД.
        """

        data = get_open_times(schema, symbol[0], period)
        data = [data[0][0], data[1][0]]
        data = pd.DataFrame(data=data, columns=['date_time'], dtype='datetime64[ns]')
        data['date_time_concat'] = data['date_time']

        pd_data_range = pd.date_range(start=period[0], end=period[1], freq='min')
        pd_data_range = pd.DataFrame(data=pd_data_range, columns=['date_time'])
        empty = pd_data_range.merge(data, on='date_time', how='left')
        empty = empty[empty['date_time_concat'].isnull()]

        params[schema][symbol]['job_times'] = empty

    first_rule()

    empty_frame = params[schema][symbol]['job_times']
    if not empty_frame.empty:
        # Если нашли незаполненные периоды, запускаем job для загрузки данных с торговой площадки.
        print(f"{date_now()}: Attention! Found missing periods. The data will be reloaded.")

        empty_frame['json'] = empty_frame.apply(
            lambda x: kline_data_1m(symbol[1],
                                    convert_to_timestamp(x['date_time']),
                                    convert_to_timestamp(x['date_time'])), axis=1)

        # Для каждой схемы должна вызываться свой JOB - нужно продумать механизм.
        # Пока будет так... Нужно поправить здесь.


def check_available_data(params: dict):
    for key_schema in params.keys():
        for key_symbol in params[key_schema].keys():
            period = params[key_schema][key_symbol]['period']
            thread = threading.Thread(target=kline_data, args=[(params, key_schema, key_symbol, period), ])
            thread.start()

            thread.join()
