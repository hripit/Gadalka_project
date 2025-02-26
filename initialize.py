from interface.app_param import message_md, mem_app, schema_md, layer_md
from pg_base.select_pg import get_all_schema, select_layers
from interface.app_uti import compare_message

from PyQt6.QtGui import *


def initialize_project():
    """Initializes the project variables, schemas, and layers."""
    try:
        # Clear existing data
        message_md.clear()
        mem_app.clear()

        # Log initialization start
        log_message("Инициализируем переменные проекта...")

        # Step 1: Initialize schemas
        initialize_schemas()

        # Step 2: Set basic metadata
        set_basic_metadata()

        # Step 3: Finalize initialization
        finalize_initialization()

    except Exception as e:
        log_error(f"Ошибка при инициализации: {e}")


def initialize_schemas():
    """Fetches and initializes available schemas."""
    try:
        log_message("Инициализируем доступные схемы...")
        schemas = get_all_schema()

        if not schemas:
            log_warning("Не обнаружено ни одной схемы.")
            return

        for schema in schemas:
            if "timeless" in schema[0]:
                initialize_schema(schema)

    except Exception as e:
        log_error(f"Ошибка при загрузке схем: {e}")


def initialize_schema(schema):
    """Initializes a single schema and its associated layers."""
    try:
        schema_name = schema[0]
        mem_app[schema_name] = {}
        schema_md.appendRow(QStandardItem(schema_name))
        log_message(f"Схема '{schema_name}' успешно добавлена.")

        # Initialize layers for the schema
        initialize_layers(schema_name)

    except Exception as e:
        log_error(f"Ошибка при инициализации схемы '{schema[0]}': {e}")


def initialize_layers(schema_name):
    """Fetches and initializes layers for a given schema."""
    try:
        log_message("Инициализируем расчетные слои...")
        layers = select_layers(schema_name)

        if not layers:
            log_warning(f"Для схемы '{schema_name}' не найдено расчетных слоев.")
            return

        for layer in layers:
            layer_name = layer[0]
            layer_data = {
                "symbol": [layer[3], layer[4]],
                "side": [layer[5], layer[6]],
                "base_asset": layer[1],
                "margin": layer[2],
                "default": layer[7],
            }

            mem_app[schema_name][layer_name] = layer_data
            layer_md.appendRow(QStandardItem(f"symbol: {layer_data['symbol']}, "
                                             f"side: {layer_data['side']}, "
                                             f"base asset: {layer_data['base_asset']}, "
                                             f"margin: {layer_data['margin']}"))
            log_message(f"Слой '{layer_name}' для схемы '{schema_name}' успешно добавлен.")

    except Exception as e:
        log_error(f"Ошибка при инициализации слоев для схемы '{schema_name}': {e}")


def set_basic_metadata():
    """Sets up basic metadata for the application."""
    try:
        mem_app['models'] = {'schemas': schema_md, 'layers': layer_md}
        mem_app['params'] = None
        mem_app['stop_thread'] = False
        log_message("Базовые метаданные установлены.")
    except Exception as e:
        log_error(f"Ошибка при установке базовых метаданных: {e}")


def finalize_initialization():
    """Finalizes the initialization process."""
    log_message("Инициализация параметров выполнена.")


# Helper Functions for Logging
def log_message(message):
    """Logs informational messages."""
    message_md.appendRow(compare_message(message))


def log_warning(message):
    """Logs warning messages."""
    message_md.appendRow(compare_message(f"Предупреждение: {message}"))


def log_error(message):
    """Logs error messages."""
    message_md.appendRow(compare_message(f"Ошибка: {message}"))