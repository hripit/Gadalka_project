import datetime
import random
import threading
from datetime import tzinfo

from pg_base.select_pg import get_open_times, get_available_periods, set_frame_to_DB
from binance_job import kline_data_1m
import pandas as pd
from uti import date_now, convert_to_timestamp, dtime_range, repack_list, convert_from_timestamp
from json import dumps


def kline_data(t_args):
    params = t_args[0]
    schema = t_args[1]
    symbol = t_args[2]

    period = get_available_periods(schema, symbol[0])

    if not period[0][0]:
        period = dtime_range()
    else:
        period = [period[0][0], period[0][1]]

    params[schema][symbol]['period'] = period

    def first_rule():
        """
        Проверим иметься ли информация для заданного периода в базе данных.
        :Заполним [params] Список значений open_time. Означает что на список дат,
        информация о прайсе отсутствует в БД.
        """

        data = get_open_times(schema, symbol[0])

        data = pd.DataFrame(data=data, columns=['date_time'], dtype='datetime64[ns]')
        data['date_time_concat'] = data['date_time']

        pd_data_range = pd.date_range(start=period[0], end=period[1], freq='min')
        pd_data_range = pd.DataFrame(data=pd_data_range, columns=['date_time'])
        empty = pd_data_range.merge(data, on='date_time', how='left')
        empty = empty[empty['date_time_concat'].isnull()]

        params[schema][symbol]['job_times'] = empty

    first_rule()

    empty_frame = params[schema][symbol]['job_times']
    # empty_frame = pd.DataFrame()
    if not empty_frame.empty:
        # Если нашли незаполненные периоды, запускаем job для загрузки данных с торговой площадки.
        print(f"{date_now()}: Attention! Found missing data for periods: [{period[0]}] :: [{period[1]}]. "
              f"The data will be reloaded.")

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
        kline_frame['date_time'] = kline_frame.apply(
            lambda x: convert_from_timestamp(x['json'][0]), axis=1)

        empty_frame = empty_frame.drop('date_time_concat', axis=1)

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

        # Добавим информацию в базу данных
        f = set_frame_to_DB(empty_frame)
        print(f)


def update_data(params: dict):
    for key_schema in params.keys():
        for key_symbol in params[key_schema].keys():
            thread = threading.Thread(target=kline_data, args=[(params, key_schema, key_symbol), ])
            thread.start()

            thread.join()
