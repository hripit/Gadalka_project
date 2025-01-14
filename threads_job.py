import datetime
import threading
from pg_base.select_pg import get_open_times
import pandas as pd


def kline_data(t_args):
    params = t_args[0]
    schema = t_args[1]
    symbol = t_args[2]
    period = t_args[3]

    def first_rule():
        """
        Первая проверка: Проверим имеется ли информация для заданного периода в базе данных.
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
        print(empty)

    first_rule()

    if not params[schema][symbol]['job_times'].empty:
        # Если нашли незаполненные периоды, запускаем job для загрузки данных с торговой площадки.
        print(1)


def check_available_data(params: dict):
    for key_schema in params.keys():
        for key_symbol in params[key_schema].keys():
            period = params[key_schema][key_symbol]['period']
            thread = threading.Thread(target=kline_data, args=[(params, key_schema, key_symbol, period), ])
            thread.start()

            thread.join()
