import datetime
import threading
from pg_base.select_pg import get_open_times
import pandas as pd


def kline_data(t_args):
    params = t_args[0]

    def first_rule(args):
        """
        Первая проверка: Проверим имеется ли информация для заданного периода в базе данных.
        :param args: [schema, symbol, period]
        :Заполним [params] Список значений open_time. Означает что на список дат,
        информация о прайсе отсутствует в БД.
        """

        data = get_open_times(args[0], args[1][0], args[2])
        data = [data[0][0], data[1][0]]
        data = pd.DataFrame(data=data, columns=['date_time'], dtype='datetime64[ns]')
        data['date_time_concat'] = data['date_time']

        pd_data_range = pd.date_range(start=args[2][0], end=args[2][1], freq='min')
        pd_data_range = pd.DataFrame(data=pd_data_range, columns=['date_time'])
        empty = pd_data_range.merge(data, on='date_time', how='left')
        empty = empty[empty['date_time_concat'].isnull()]

        params[args[0]][args[1]]['job_times'] = empty
        print(empty)

    first_rule([t_args[1], t_args[2], t_args[3]])


def check_available_data(params: dict):
    for key_schema in params.keys():
        for key_symbol in params[key_schema].keys():
            period = params[key_schema][key_symbol]['period']
            thread = threading.Thread(target=kline_data, args=[(params, key_schema, key_symbol, period), ])
            thread.start()

            thread.join()
