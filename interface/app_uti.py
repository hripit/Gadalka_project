import datetime

from PyQt6.QtGui import QStandardItem


def compare_message(message: str):
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return QStandardItem(f'''{dt}: {message}''')
