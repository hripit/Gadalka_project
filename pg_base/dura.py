import datetime
from dateutil.relativedelta import relativedelta
from pg_base.select_pg import get_line_by_week
import os
import subprocess
import pandas as pd
import numpy as np
import time
from functools import wraps
from datetime import datetime, timedelta


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


def to_xlxs(dframe):
    # Путь к файлу Excel
    file_path = f'{coin}-{symbol}-{f"{week_day:02d}"}.xlsx'

    if not remove_file_with_retry(file_path):
        return

    main_shet = f'{coin}-{symbol}-describe'

    # # Создаем объект ExcelWriter с использованием движка xlsxwriter
    with pd.ExcelWriter(file_path, engine='xlsxwriter', datetime_format="DD.MM HH:MM") as writer:
        dframe.to_excel(writer, sheet_name=main_shet, index=False, startcol=0, startrow=1, header=False)

        workbook = writer.book
        worksheet = writer.sheets[main_shet]

        num_cols = len(dframe.columns)  # Количество столбцов

        # Устанавливаем формат для столбцов с датой/временем
        date_format = workbook.add_format({'num_format': "DD.MM HH:MM"})
        #
        for col_num in range(1, num_cols):
            if col_num == 2:
                continue
            col_letter = get_column_letter(col_num)  # Преобразуем номер столбца в букву ('D', 'E', 'F')
            worksheet.set_column(f"{col_letter}:{col_letter}", None, date_format)

        table = {'style': 'Table Style Light 9',
                 'columns': [{'header': column} for column in dframe.columns],
                 'banded_columns': True,
                 }

        sheet = writer.sheets[main_shet]

        sheet.add_table(0, 0, dframe.shape[0], dframe.shape[1] - 1, table)
        sheet.freeze_panes(1, 2)
        sheet.autofit()

        # # Добавляем трехцветную шкалу для каждой строки, начиная с четвертого столбца
        # for row_num in range(2, dframe.shape[0] + 2):  # Начинаем со второй строки (Excel индексация с 1)
        #     start_col = 3
        #     end_col = num_cols  # Последний столбец
        #
        #     # Определяем диапазон ячеек для условного форматирования по строкам
        #     start_cell = f"{get_column_letter(start_col)}{row_num}"  # Начало строки (например, D2)
        #     end_cell = f"{get_column_letter(end_col)}{row_num}"  # Конец строки (например, F2)
        #
        #     # Добавляем трехцветную шкалу для текущей строки
        #     worksheet.conditional_format(f"{start_cell}:{end_cell}", {
        #         'type': '3_color_scale',
        #         'min_color': '#FF6A6A',  # Красный (минимум)
        #         'mid_color': '#FFF68F',  # Желтый (среднее)
        #         'max_color': '#3CB371',  # Зеленый (максимум)
        #     })

        # Добавляем трехцветную шкалу для каждого столбца, начиная с третьего
        for col_num in range(2, min(25, num_cols)):  # Начинаем с третьего столбца (индекс 3)
            col_letter = get_column_letter(col_num)
            # Определяем диапазон ячеек для условного форматирования
            start_cell = f"{col_letter}2"  # Начинаем со второй строки (первая строка - заголовок)
            end_cell = f"{col_letter}{dframe.shape[0] + 1}"  # Последняя строка данных

            # Добавляем трехцветную шкалу
            worksheet.conditional_format(f"{start_cell}:{end_cell}", {
                'type': '3_color_scale',
                'min_color': '#3CB371',
                'mid_color': '#FFF68F',  # Желтый (среднее)
                'max_color': '#FF6A6A',
            })

        if num_cols > 25:
            for row_num in range(2, dframe.shape[0] + 2):  # Начинаем со второй строки
                start_col = min(25, num_cols)  # Ограничиваем диапазон до последнего столбца

                start_cell = f"{get_column_letter(start_col)}{row_num}"
                end_cell = f"{get_column_letter(num_cols)}{row_num}"

                worksheet.conditional_format(f"{start_cell}:{end_cell}", {
                    'type': '3_color_scale',
                    'min_color': '#3CB371',
                    'mid_color': '#FFF68F',  # Желтый (среднее)
                    'max_color': '#FF6A6A',
                })
    # Открываем файл Excel после завершения
    subprocess.run(['start', file_path], shell=True)  # Для Windows
    print("DataFrame успешно выгружен в output.xlsx с цветовой шкалой и фиксацией области")


@measure_execution_time
def generate_frame():
    end_dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0, )
    start_dt = end_dt - relativedelta(years=1)
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    dt_frame = pd.date_range(start_dt, end_dt, freq='min')
    dt_frame = dt_frame[dt_frame.dayofweek == week_day]

    # Преобразуем диапазон дат в DataFrame
    dt_frame = pd.DataFrame(dt_frame, columns=['open_time'])

    response_frame = get_line_by_week(start_dt, end_dt, coin, symbol, margin, base_asset)
    merged_df = pd.merge(dt_frame, response_frame, on='open_time', how='left')

    merged_df['hour_minute'] = (pd.to_timedelta(merged_df['open_time'].dt.hour, unit='h')
                                + pd.to_timedelta(merged_df['open_time'].dt.minute, unit='m'))

    # Преобразуем столбец 'hour_minute' в timedelta
    merged_df['hour_minute'] = pd.to_timedelta(merged_df['hour_minute'])

    # Получаем текущую дату
    current_date = pd.Timestamp.now().date()
    # Преобразуем текущую дату в Timestamp
    current_timestamp = pd.Timestamp(current_date)
    # Складываем дату и временной интервал
    merged_df['hour_minute'] = current_timestamp + merged_df['hour_minute']
    merged_df['hour_minute'] = merged_df['hour_minute'].dt.floor('min')
    del merged_df['open_time']

    merged_df = merged_df.groupby(['hour_minute'], as_index=False).mean()
    merged_df['time_left'] = merged_df['time_left'].dt.floor('min')

    return merged_df


@measure_execution_time
# Функция для поиска самой длинной цепочки
def find_longest_chain(df):
    max_chain_length = 0
    longest_chain = []

    def find_next(start_time: None, end_time):
        current_start_time = row['hour_minute']
        current_duration = row['time_left']
        current_end_time = current_start_time + current_duration

        return next_time

    # Проходим по каждой строке DataFrame
    for _, row in df.iterrows():
        current_start_time = row['hour_minute']
        current_duration = row['time_left']
        current_end_time = current_start_time + current_duration

        # Инициализируем текущую цепочку
        current_chain = [row]
        current_chain_length = 1

        # Находим следующие события, которые попадают в цепочку
        next_event = df[(df['hour_minute'] > current_start_time) & (df['hour_minute'] <= current_end_time)]

        while not next_event.empty:
            # Берём первую строку из найденных событий
            next_row = next_event.iloc[0]
            next_start_time = next_row['hour_minute']
            next_duration = next_row['time_left']
            next_end_time = next_start_time + next_duration

            # Добавляем событие в текущую цепочку
            current_chain.append(next_row)
            current_chain_length += 1

            # Обновляем время окончания цепочки
            current_end_time = next_end_time

            # Ищем следующие события
            next_event = df[(df['hour_minute'] > next_start_time) & (df['hour_minute'] <= next_end_time)]

        # Проверяем, является ли текущая цепочка самой длинной
        if current_chain_length > max_chain_length:
            max_chain_length = current_chain_length
            longest_chain = current_chain

    return max_chain_length, longest_chain


if __name__ == '__main__':
    coin = 'WIF'
    # coin = 'BTC'
    symbol = 'WIFUSDT'
    # symbol = 'ETHBTC'
    margin = 0.002
    # margin = 0.01
    base_asset = 100
    # base_asset = '0.0055'

    week_day = datetime.now().weekday()
    # week_day = 4

    frame = generate_frame()[0]

    # Поиск самой длинной цепочки
    max_chain_length, longest_chain = find_longest_chain(frame)

    # Вывод результатов
    print(f"Максимальная длина цепочки: {max_chain_length}")
    print("Самая длинная цепочка:")
    for event in longest_chain:
        print(f"Начало: {event[0]}, Продолжительность: {event[1]} минут")
    # Выводим результат
    to_xlxs(frame)
