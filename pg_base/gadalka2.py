import datetime
from dateutil.relativedelta import relativedelta
from pg_base.select_pg import get_line_by_week
import os
import subprocess
import pandas as pd
import numpy as np
pd.set_option('future.no_silent_downcasting', True)

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


def to_xlxs(frame):
    # Путь к файлу Excel
    file_path = 'output.xlsx'

    # Удаляем файл, если он уже существует (перезапись)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Создаем объект ExcelWriter с использованием движка xlsxwriter
    with pd.ExcelWriter(file_path, engine='xlsxwriter', datetime_format="DD.MM HH:MM") as writer:
        # Выгружаем DataFrame в Excel
        frame.to_excel(writer, sheet_name='Sheet1', index=False, startrow=1)  # Добавляем отступ для заголовка

        # Получаем доступ к workbook и worksheet
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Фиксируем первую строку (заголовки) и первый столбец
        worksheet.freeze_panes(2, 4)  # Закрепляем строку 1 и столбец 1 (нумерация с 0)

        # Добавляем фильтр для всего диапазона данных
        num_rows = len(frame)  # Количество строк
        num_cols = len(frame.columns)  # Количество столбцов
        # worksheet.autofilter(2, 1, num_rows, num_cols - 1)  # Добавляем фильтр
        last_row = num_rows + 1  # Последняя строка с учетом заголовков
        last_col_letter = get_column_letter(num_cols - 1)  # Буква последнего столбца
        table_range = f"$A$2:${last_col_letter}${last_row + 1}"

        # Устанавливаем формат для столбцов с датой/временем
        date_format = workbook.add_format({'num_format': "DD.MM HH:MM"})  # Формат даты/времени

        for col_num in range(3, num_cols):  # Столбцы 3, 4, 5 (Python индексация с 0)
            col_letter = get_column_letter(col_num)  # Преобразуем номер столбца в букву ('D', 'E', 'F')
            # Применяем формат к диапазону
            worksheet.set_column(f"{col_letter}:{col_letter}", None, date_format)

            # Для каждого столбца, начиная с третьего, применяем форматирование
            for colum in range(3, num_cols):  # Столбцы, начиная с column3
                col_letter = get_column_letter(colum)  # Преобразуем номер столбца в букву ('D', 'E', ...)
                range_str = f"${col_letter}${2}:${col_letter}${last_row + 1}"
                # Применяем трехцветную шкалу для текущего часа
                worksheet.conditional_format(range_str, {
                    'type': '3_color_scale',
                    'min_color': '#3CB371',  # Красный
                    'mid_color': '#FFF68F',  # Желтый
                    'max_color': '#FF6A6A',  # Зеленый
                })

        # unique_hours = frame['hour'].unique()
        # # Применяем форматирование для каждого часа
        # start_row = 1  # Начальная строка после заголовков
        # for hour in unique_hours:
        #     # Отфильтровываем строки для текущего часа
        #     hour_data = frame[frame['hour'] == hour]
        #     hour_rows = len(hour_data)
        #
        #     # Для каждого столбца, начиная с третьего, применяем форматирование
        #     for col_num in range(3, num_cols):  # Столбцы, начиная с column3
        #         col_letter = get_column_letter(col_num)  # Преобразуем номер столбца в букву ('D', 'E', ...)
        #         range_str = f"{col_letter}{start_row + 1}:{col_letter}{start_row + hour_rows}"  # Диапазон для текущего часа
        #
        #         # Применяем трехцветную шкалу для текущего часа
        #         worksheet.conditional_format(range_str, {
        #             'type': '3_color_scale',
        #             'min_value': hour_data.iloc[:, col_num].min(),
        #             'mid_value': hour_data.iloc[:, col_num].quantile(0.5),
        #             'max_value': hour_data.iloc[:, col_num].max(),
        #             'min_type': 'num',
        #             'mid_type': 'num',
        #             'max_type': 'num',
        #             'min_color': '#FF6A6A',  # Красный
        #             'mid_color': '#FFF68F',  # Желтый
        #             'max_color': '#3CB371'  # Зеленый
        #         })
        #
        #     # Обновляем начальную строку для следующего часа
        #     start_row += hour_rows
        column_settings = [{'header': column} for column in frame.columns]
        worksheet.add_table(table_range, {'columns': column_settings})

    # Открываем файл Excel после завершения
    subprocess.run(['start', file_path], shell=True)  # Для Windows
    print("DataFrame успешно выгружен в output.xlsx с цветовой шкалой и фиксацией области")


if __name__ == '__main__':

    end_dt = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0, )
    start_dt = end_dt - relativedelta(years=1)
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    delta_days = (end_dt - start_dt).days

    dt_frame = pd.date_range(start_dt, end_dt, freq='min')

    day_of_week = 3  # 0 - Понедельник, 1 - Вторник, ..., 6 - Воскресенье
    dt_frame = dt_frame[dt_frame.dayofweek == day_of_week]

    # Преобразуем диапазон дат в DataFrame
    dt_frame = pd.DataFrame(dt_frame, columns=['open_time'])

    # Добавляем столбцы с днем недели, часом и минутой
    dt_frame['day_of_week'] = dt_frame['open_time'].dt.day_name()  # День недели (название)
    dt_frame['hour'] = dt_frame['open_time'].dt.hour  # Час
    dt_frame['minute'] = dt_frame['open_time'].dt.minute  # Минута

    # Количество полных недель
    weeks_between = delta_days // 7
    merged_df = pd.DataFrame()
    # weeks_between = 2
    for i in range(0, weeks_between + 1):
        ind_week = 'week_' + f"{i:02d}"
        response_frame = get_line_by_week(i, ind_week)

        if merged_df.empty:
            merged_df = pd.merge(dt_frame, response_frame, on='open_time', how='outer')
        else:
            merged_df = pd.merge(merged_df, response_frame, on='open_time', how='outer')
    del merged_df['open_time']
    # merged_df = merged_df.fillna(pd.to_timedelta(0))
    # Группируем по дню недели, часу и минуте, вычисляем средние значения для column1, column2, column3
    merged_df = merged_df.groupby(['day_of_week', 'hour', 'minute'], as_index=False).mean()
    # Добавляем столбец "итог_среднее" как среднее от всех столбцов, кроме column1
    columns_to = merged_df.columns.difference(['week_00', 'day_of_week', 'hour', 'minute'])
    merged_df = merged_df.fillna(pd.to_timedelta(0)).infer_objects()

    # Преобразуем все столбцы типа timedelta64[ns] в наносекунды
    numeric_df = merged_df[columns_to].apply(
        lambda col: col.astype('int64') if col.dtype == 'timedelta64[ns]' else col)
    # Вычисляем среднее значение по строкам
    merged_df['итог_mean'] = numeric_df.mean(axis=1)
    merged_df['итог_mean'] = pd.to_timedelta(merged_df['итог_mean']).dt.floor('s')
    merged_df['итог_median'] = numeric_df[columns_to].median(axis=1)
    merged_df['итог_median'] = pd.to_timedelta(merged_df['итог_median']).dt.floor('s')
    merged_df['итог_std'] = numeric_df[columns_to].std(axis=1)
    merged_df['итог_std'] = pd.to_timedelta(merged_df['итог_std']).dt.floor('s')
    cnt = 3
    # Создаем последовательность от 0.1 до 1 с шагом 0.05
    alphas = np.arange(0.1, 1.1, 0.1)
    for h in alphas:
        h = round(h, 2)
        # merged_df[f'итог_ewn_aplha_{h}'] = merged_df[columns_to].ewm(halflife=round(h,3), adjust=False).mean().mean(axis=1)
        merged_df[f'итог_quantile_{h}'] = merged_df[columns_to].quantile(h, axis=1).dt.floor('s')
        cnt += 1
        #
        # .rolling(window=3)

    # Получаем список всех столбцов
    columns = list(merged_df.columns)

    # Разделяем столбцы на три части:
    first_part = columns[:4]
    last_three = columns[-cnt:]
    middle_part = columns[4:-cnt]
    new_order = first_part + last_three + middle_part
    merged_df = merged_df[new_order]

    # Выводим результат
    to_xlxs(merged_df)
    print('done')
