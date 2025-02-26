# Стандартная библиотека Python
import os, sys, time
from copy import deepcopy

# Добавляем родительскую директорию (где лежит uti.py) в sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Текущая директория
parent_dir = os.path.dirname(current_dir)  # Родительская директория
sys.path.append(parent_dir)

# Локальные модули
from uti import date_now
from pg_base.select_pg import get_all_schema, get_symbols_data

# Внешние библиотеки
from termcolor import colored

# Приложение-специфичные модули
from binance_job import Lets_start_job

# Инициализация параметров
params = {}


def init_params():
    """
    Инициализирует параметры для работы с символами и схемами.
    """
    schemas = get_all_schema()
    template_dict = {
        'period': [],
        'job_times': []
    }

    for schema in schemas:
        if 'timeless' in schema[0]:  # Проверяем наличие подстроки 'timeless'
            symbols = get_symbols_data(schema[0])
            if not symbols:  # Пропускаем пустые символы
                continue

            params[schema[0]] = {symbol: deepcopy(template_dict) for symbol in symbols}


def sleep_until_next_minute():
    """
    Ждет до начала следующей минуты.
    """
    current_time = time.time()
    seconds_until_next_minute = 60 - (current_time % 60)
    time.sleep(seconds_until_next_minute)


def get_prices():
    """
    Основной цикл для запроса исторической информации о ценах.
    """
    print(colored(f"{date_now()}: Скрипт для получения исторической информации "
                  f"о ценах на торговых платформах [по списку]", 'magenta'))

    # Инициализация параметров
    init_params()

    while True:
        # Выполнение задачи
        print(colored(f"{date_now()}: Получение исторической информации "
                      f"о ценах на торговых платформах [по списку]", 'magenta'))
        Lets_start_job(params)

        # Ждем до начала следующей минуты
        sleep_until_next_minute()


if __name__ == '__main__':
    get_prices()
