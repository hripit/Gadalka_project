from PyQt6.QtGui import *

# Будем подсвечивать сообщения
message_md = QStandardItemModel()
layer_md = QStandardItemModel()
schema_md = QStandardItem()

mem_app = dict()

orders_model = QStandardItemModel()
orders_imd = dict()
thread_list = list()

stop_thread = False
