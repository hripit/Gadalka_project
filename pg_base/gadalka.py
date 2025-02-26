# Стандартная библиотека Python
import datetime
import os
import subprocess
import time
import threading
from functools import wraps
from dateutil.relativedelta import relativedelta

# Внешние библиотеки
import pandas as pd
import numpy as np

# Локальные модули
from pg_base.select_pg import get_line_by_week
from uti import date_now


def measure_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Время выполнения функции '{func.__name__}': {elapsed_time:.6f} секунд")
        return result, elapsed_time  # Возвращаем результат функции и время выполнения

    return wrapper


def remove_file_with_retry(file_path, retries=10, delay=10):
    """
    Удаляет файл с возможностью повторных попыток, если файл занят.

    :param file_path: Путь к файлу для удаления.
    :param retries: Количество попыток удаления (по умолчанию 10).
    :param delay: Задержка между попытками в секундах (по умолчанию 1 секунда).
    :return: True, если файл успешно удален; False, если все попытки неудачны.
    """

    for attempt in range(retries):
        try:
            os.remove(file_path)
            print(f"Файл успешно удален: {file_path}")
            return True  # Возвращаем True при успешном удалении
        except PermissionError:
            if attempt < retries - 1:  # Если это не последняя попытка
                print(f"Файл занят. Попытка {attempt + 1} из {retries}. Ожидание {delay} секунд...")
                time.sleep(delay)  # Ждем перед следующей попыткой
            else:
                print(f"Не удалось удалить файл после {retries} попыток.")
        except Exception as e:
            print(f"Произошла ошибка при удалении файла: {e}")
            return True  # Возвращаем False при другой ошибке

    return False  # Возвращаем False, если все попытки неудачны


def get_column_letter(col_num):
    """
    Преобразует номер столбца (0-based) в буквенное обозначение Excel.
    Например:
    0 -> 'A', 1 -> 'B', ..., 25 -> 'Z', 26 -> 'AA', 27 -> 'AB', и т.д.
    """
    letters = []
    while col_num >= 0:
        col_num, remainder = divmod(col_num, 26)
        letters.append(chr(65 + remainder))
        col_num -= 1
    return ''.join(reversed(letters))


def to_xlxs(dframe, merged_frame, symbol: str, coin: str, w_day: str):
    # Путь к файлу Excel
    file_path = f'{coin}-{symbol}-{f"{w_day:02d}"}.xlsx'
    if not remove_file_with_retry(file_path):
        return
    main_sheet = f'{coin}-{symbol}-describe'
    merged_sheet = f'{coin}-{symbol}-merged'

    # Создаем объект ExcelWriter с использованием движка xlsxwriter
    with pd.ExcelWriter(file_path, engine='xlsxwriter', datetime_format="DD.MM HH:MM") as writer:
        # Записываем dframe на первый лист
        dframe.to_excel(writer, sheet_name=main_sheet, index=False, startcol=0, startrow=1, header=False)

        # Записываем merged_frame на второй лист
        merged_frame.to_excel(writer, sheet_name=merged_sheet, index=False, startcol=0, startrow=1, header=False)

        workbook = writer.book

        # Форматирование первого листа (dframe)
        worksheet_main = writer.sheets[main_sheet]
        format_and_style(worksheet_main, dframe, workbook)

        # Форматирование второго листа (merged_frame)
        worksheet_merged = writer.sheets[merged_sheet]
        format_and_style(worksheet_merged, merged_frame, workbook)

    # Открываем файл Excel после завершения
    subprocess.run(['start', file_path], shell=True)  # Для Windows
    print(f"DataFrame успешно выгружен в {file_path} с цветовой шкалой и фиксацией области")


def format_and_style(worksheet, dataframe, workbook):
    """
    Применяет общее форматирование и стиль к листу.

    :param worksheet: Лист Excel для форматирования.
    :param dataframe: DataFrame для применения стиля.
    :param workbook: Объект Workbook из XlsxWriter.
    """
    num_cols = len(dataframe.columns)  # Количество столбцов

    # Устанавливаем формат для столбцов с датой/временем
    date_format = workbook.add_format({'num_format': "DD.MM HH:MM"})
    for col_num in range(1, num_cols):
        if col_num == 2:
            continue
        col_letter = get_column_letter(col_num)  # Преобразуем номер столбца в букву ('D', 'E', 'F')
        worksheet.set_column(f"{col_letter}:{col_letter}", None, date_format)

    # Создаем таблицу
    table = {'style': 'Table Style Light 9',
             'columns': [{'header': column} for column in dataframe.columns],
             'banded_columns': True,
             }
    worksheet.add_table(0, 0, dataframe.shape[0], dataframe.shape[1] - 1, table)
    worksheet.freeze_panes(1, 2)
    worksheet.autofit()

    # Добавляем трехцветную шкалу для каждого столбца, начиная с третьего
    for col_num in range(2, min(25, num_cols)):  # Начинаем с третьего столбца (индекс 3)
        col_letter = get_column_letter(col_num)
        start_cell = f"{col_letter}2"  # Начинаем со второй строки
        end_cell = f"{col_letter}{dataframe.shape[0] + 1}"  # Последняя строка данных
        worksheet.conditional_format(f"{start_cell}:{end_cell}", {
            'type': '3_color_scale',
            'min_color': '#3CB371',  # Зеленый
            'mid_color': '#FFF68F',  # Желтый
            'max_color': '#FF6A6A',  # Красный
        })

    # Добавляем трехцветную шкалу для строк, если количество столбцов > 25
    if num_cols > 25:
        for row_num in range(2, dataframe.shape[0] + 2):  # Начинаем со второй строки
            start_col = min(25, num_cols)  # Ограничиваем диапазон до последнего столбца
            start_cell = f"{get_column_letter(start_col)}{row_num}"
            end_cell = f"{get_column_letter(num_cols)}{row_num}"
            worksheet.conditional_format(f"{start_cell}:{end_cell}", {
                'type': '3_color_scale',
                'min_color': '#3CB371',  # Зеленый
                'mid_color': '#FFF68F',  # Желтый
                'max_color': '#FF6A6A',  # Красный
            })


@measure_execution_time
def generate_frame(symbol: str, coin: str, margin: str, base_asset: str, w_day: int):
    end_dt = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0, )
    start_dt = end_dt - relativedelta(years=1)
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    dt_frame = pd.date_range(start_dt, end_dt, freq='min')
    dt_frame = dt_frame[dt_frame.dayofweek == w_day]

    # Преобразуем диапазон дат в DataFrame
    dt_frame = pd.DataFrame(dt_frame, columns=['open_time'])

    response_frame = get_line_by_week(start_dt, end_dt, coin, symbol, margin, base_asset)
    merged_df = pd.merge(dt_frame, response_frame, on='open_time', how='left')

    # Добавляем столбцы с днем недели, часом и минутой
    merged_df['day_of_week'] = merged_df['open_time'].dt.day_name()  # День недели (название)

    merged_df['td'] = (pd.to_timedelta(merged_df['open_time'].dt.hour, unit='h')
                       + pd.to_timedelta(merged_df['open_time'].dt.minute, unit='m'))

    if merged_df[['open_time']].duplicated().any():
        print(" содержит дубликаты! open_time", merged_df[merged_df[['open_time']].duplicated(keep=False)])

    return merged_df


@measure_execution_time
def get_percentile(dframe):
    del dframe['open_time']

    percentiles = np.arange(0.1, 1, 0.05)
    percentiles = np.round(percentiles, 2)

    dframe = dframe.groupby(['day_of_week', 'td'], as_index=False).describe(percentiles=percentiles)

    dframe.columns = dframe.columns.droplevel(0)
    dframe.columns.values[0] = 'day_of_week'
    dframe.columns.values[1] = 'hour_minute'

    # Преобразуем столбец 'hour_minute' в timedelta
    dframe['hour_minute'] = pd.to_timedelta(dframe['hour_minute'])

    # Получаем текущую дату
    current_date = pd.Timestamp.now().date()
    # Преобразуем текущую дату в Timestamp
    current_timestamp = pd.Timestamp(current_date)
    # Складываем дату и временной интервал
    dframe['hour_minute'] = current_timestamp + dframe['hour_minute']
    dframe['hour_minute'] = dframe['hour_minute'].dt.floor('min')

    # Преобразуем столбец 'count' в числовой формат, заменяя ошибочные значения на NaN
    dframe['count'] = pd.to_numeric(dframe['count'], errors='coerce')

    # Преобразуем столбцы с 2 по 5 (индексы 1 по 4) в timedelta
    dframe['count'] = pd.to_numeric(dframe['count'], errors='coerce')

    for col in dframe.columns[3:len(dframe.columns)]:  # Выбираем столбцы с индексами 1, 2, 3, 4
        try:
            dframe[col] = pd.to_timedelta(dframe[col], errors='coerce')
            dframe[col] = dframe[col] + pd.Timestamp('1900-01-01')
            dframe[col] = dframe[col].dt.floor('min')

        except Exception as e:
            print(f"Ошибка при преобразовании столбца {col}: {e}")

    return dframe


@measure_execution_time
def gen_frames_by_weeks(symbol: str, coin: str, margin: float, base_asset: float, w_day: int):
    cnt_weeks = 52
    merged_weeks = pd.DataFrame()
    correct_day = datetime.datetime.now().weekday() - w_day

    for w in range(0, cnt_weeks):
        end_dt = datetime.datetime.now().replace(microsecond=0, second=0, minute=59, hour=23)
        end_dt = end_dt - relativedelta(days=correct_day)
        end_dt = end_dt - relativedelta(weeks=w)
        start_dt = end_dt.replace(microsecond=0, second=0, minute=0, hour=0)

        dt_frame = pd.date_range(start_dt, end_dt, freq='min')

        dt_frame = pd.DataFrame(dt_frame, columns=['open_time'])

        response_frame = get_line_by_week(start_dt, end_dt, coin, symbol, margin, base_asset)
        response_frame = response_frame.rename(columns={response_frame.columns[1]: 'week_' + f"{w:02d}"})

        merged_df = pd.merge(dt_frame, response_frame, on=['open_time'], how='left')

        if merged_weeks.empty:
            merged_weeks = merged_df
        else:
            if not response_frame['week_' + f"{w:02d}"].isnull().all():
                merged_weeks = pd.merge(merged_weeks, merged_df, on=['open_time'], how='outer')

    for col in merged_weeks.columns[1:len(merged_weeks.columns)]:  # Выбираем столбцы с индексами 1, 2, 3, 4
        try:
            merged_weeks[col] = pd.to_timedelta(merged_weeks[col], errors='coerce')
            merged_weeks[col] = merged_weeks[col] + pd.Timestamp('1900-01-01')
            merged_weeks[col] = merged_weeks[col].dt.floor('min')
        except Exception as e:
            print(f"Ошибка при преобразовании столбца {col}: {e}")

    merged_weeks['day_of_week'] = merged_weeks['open_time'].dt.day_name()  # День недели (название)
    merged_weeks['hour_minute'] = (pd.to_timedelta(merged_weeks['open_time'].dt.hour, unit='h')
                                   + pd.to_timedelta(merged_weeks['open_time'].dt.minute, unit='m'))
    # Преобразуем столбец 'hour_minute' в timedelta
    merged_weeks['hour_minute'] = pd.to_timedelta(merged_weeks['hour_minute'])
    # Получаем текущую дату
    current_date = pd.Timestamp.now().date()
    # Преобразуем текущую дату в Timestamp
    current_timestamp = pd.Timestamp(current_date)
    # Складываем дату и временной интервал
    merged_weeks['hour_minute'] = current_timestamp + merged_weeks['hour_minute']
    merged_weeks['hour_minute'] = merged_weeks['hour_minute'].dt.floor('min')
    del merged_weeks['open_time']
    merged_weeks = merged_weeks.groupby(['day_of_week', 'hour_minute'], as_index=False).mean()

    return merged_weeks


@measure_execution_time
def find_n_min_mean_by_hour(dataframe, hour_column='hour_minute', mean_column='mean', n=2):
    """
    Находит две строки с минимальным значением 'mean' для каждого часа.

    :param dataframe: Исходный DataFrame.
    :param hour_column: Название столбца с временными метками (по умолчанию 'hour_minute').
    :param mean_column: Название столбца со значениями 'mean' (по умолчанию 'mean').
    :return: DataFrame с двумя минимальными значениями 'mean' для каждого часа.
    """
    if dataframe.empty:
        return pd.DataFrame()  # Возвращаем пустой DataFrame, если входные данные пустые

    # Создаем пустой список для хранения результатов
    result = []

    # Группировка по часам и выбор двух минимальных значений 'mean'
    for hour, group in dataframe.groupby(dataframe[hour_column].dt.hour):
        # Выбираем две строки с минимальными значениями 'mean'
        n_min_rows = group.nsmallest(n, mean_column)
        result.append(n_min_rows)

    # Объединяем результаты в один DataFrame
    return pd.concat(result).reset_index(drop=True)


@measure_execution_time
def filter_by_mean_count(dataframe, count_column='count'):
    """
    Фильтрует DataFrame, оставляя строки, где значения в столбце 'count' больше или равны среднему значению.

    :param dataframe: Исходный DataFrame.
    :param count_column: Название столбца со значениями 'count' (по умолчанию 'count').
    :return: Отфильтрованный DataFrame.
    """
    if dataframe.empty:
        return pd.DataFrame()  # Возвращаем пустой DataFrame, если входные данные пустые

    # Вычисление среднего значения 'count'
    mean_count = int(dataframe[count_column].mean())

    # Фильтрация строк
    return dataframe[dataframe[count_column] >= mean_count]


if __name__ == '__main__':
    layers = [
        ['WIFUSDT', 'WIF', 0.002, 100],
        # ['WIFUSDT', 'USDT', 0.002, 100],
        # ['ETHBTC', 'BTC', 0.01, 0.0055],
        # ['ETHBTC', 'ETH', 0.01, 0.0055]
    ]

    def process_week_day(w_day):
        """Функция для обработки данных для конкретного дня недели."""
        for lay in layers:
            s, c, m, b = lay

            print(f'{date_now()}: Подготовим расчет для: [день недели: {w_day}, {lay}]')

            # Генерация данных
            frame = generate_frame(symbol=s, coin=c, margin=m, base_asset=b, w_day=w_day)[0]
            weeks = gen_frames_by_weeks(symbol=s, coin=c, margin=m, base_asset=b, w_day=w_day)[0]

            # Проверка на пустые DataFrame
            if frame.empty or weeks.empty:
                continue

            # Вычисление percentile-данных
            percentile_frame = get_percentile(frame)[0]

            if percentile_frame.empty:
                continue

            # Объединение данных
            merged_frame = pd.merge(percentile_frame, weeks, on=['day_of_week', 'hour_minute'], how='left')

            if merged_frame.empty:
                continue

            # Фильтрация по среднему значению 'count'
            filtered_frame = filter_by_mean_count(merged_frame, count_column='count')[0]

            if filtered_frame.empty:
                continue

            # Поиск строк с минимальным 'mean' для каждого часа
            result_frame = find_n_min_mean_by_hour(filtered_frame, hour_column='hour_minute', mean_column='mean')[0]

            if result_frame.empty:
                continue

            # Сохранение результата в Excel
            to_xlxs(result_frame, merged_frame, s, c, w_day)

    # Спрашиваем у пользователя, какой день недели анализировать
    user_input = input("""
Какой день недели анализировать?
- Пусто: текущая неделя (день недели зависит от сегодняшнего дня)
- *: вся неделя (все дни недели)
- 0-6: конкретный день недели (0 - понедельник, 1 - вторник, 2 - среда, 3 - четверг, 4 - пятница, 5 - суббота, 6 - воскресенье)

Ваш выбор: """).strip()

    threads = []

    if user_input == "":
        print('Выбран параметр текущая неделя...')
        current_week_day = datetime.datetime.now().weekday()
        thread = threading.Thread(target=process_week_day, args=(current_week_day,))
        threads.append(thread)
        thread.start()

    elif user_input == "*":
        print('Выбран параметр вся неделя...')
        for week_day in range(0, 7):  # Все дни недели (0-6)
            thread = threading.Thread(target=process_week_day, args=(week_day,))
            threads.append(thread)
            thread.start()

    elif user_input.isdigit() and 0 <= int(user_input) <= 6:
        print('Выбран параметр конкретный день...')
        week_day = int(user_input)
        thread = threading.Thread(target=process_week_day, args=(week_day,))
        threads.append(thread)
        thread.start()

    else:  # Неверный ввод
        print("Неверный ввод. Анализ отменен.")
        exit()

    # Ждем завершения всех потоков
    for thread in threads:
        thread.join()

    print("Обработка завершена.")
