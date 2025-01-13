import threading
from pg_base.select_pg import get_open_times
import pandas as pd


def check_available_data(params: dict):
    def kline_data(args):
        """
        Первая проверка: Получим open_time за период...
        :param args:  [schema, symbol, period]
        :return: Список значений open_time
        """
        data = get_open_times(args[0], args[1][0], args[2])

        pd_data_range = pd.date_range(start=args[2][0], end=args[2][1], freq='min', normalize=True)

        print(data)

    for key_schema in params.keys():
        for key_symbol in params[key_schema].keys():
            period = params[key_schema][key_symbol]['period']
            thread = threading.Thread(target=kline_data, args=[(key_schema, key_symbol, period), ])
            thread.start()

            thread.join()
