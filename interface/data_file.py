import os, sys
import secrets
from binance.error import ClientError
from binance.spot import Spot
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import psutil

# Константы
SECRET_FILE_NAME = "secret.key"
USB_DRIVE_LABEL = "SECRET_KEY"  # Метка тома флешки
SALT_SIZE = 16  # Размер соли (16 байт)
ITERATIONS = 100_000  # Количество итераций для KDF

# Глобальные параметры API
PARAMS_API = {
    "api_key": None,
    "api_secret": None,
    "encrypted_api_key": None,  # Зашифрованный api_key
    "encrypted_api_secret": None  # Зашифрованный api_secret
}


def get_connection_binance():
    """Создаёт соединение с Binance, используя PARAMS_API."""
    try:
        # Шаг 1: Проверяем, заполнены ли параметры
        if not PARAMS_API["api_key"] or not PARAMS_API["api_secret"]:
            load_api_keys_from_usb()

        # Шаг 2: Создаём соединение с Binance
        if PARAMS_API["api_key"] and PARAMS_API["api_secret"]:
            connection = Spot(PARAMS_API["api_key"], PARAMS_API["api_secret"])
            return connection
        else:
            raise ValueError("API ключи не загружены.")

    except Exception as e:
        print(f"Ошибка при создании соединения: {e}")
        return False


def load_api_keys_from_usb():
    """Загружает API ключи с флешки и сохраняет их в PARAMS_API."""
    try:
        # Шаг 1: Проверяем наличие флешки
        usb_path = check_usb_drive()
        if not usb_path:
            raise FileNotFoundError("Флешка с меткой '{}' не найдена.".format(USB_DRIVE_LABEL))

        secret_file_path = os.path.join(usb_path, SECRET_FILE_NAME)
        if not os.path.exists(secret_file_path):
            raise FileNotFoundError("Файл '{}' не найден на флешке.".format(SECRET_FILE_NAME))

        # Шаг 2: Запрашиваем пароль для расшифровки
        password = request_password()
        if not password:
            raise ValueError("Пароль не был предоставлен.")

        # Шаг 3: Расшифровываем секретный ключ
        decrypted_key_data = decrypt_secret_key(secret_file_path, password)
        if not decrypted_key_data:
            raise ValueError("Не удалось расшифровать секретный ключ.")

        # Шаг 4: Извлекаем api_key и api_secret
        api_key, api_secret = parse_decrypted_key(decrypted_key_data)

        # Шаг 5: Сохраняем ключи в PARAMS_API
        PARAMS_API["api_key"] = api_key
        PARAMS_API["api_secret"] = api_secret

        # Шаг 6: Зашифровываем ключи в памяти
        encrypt_api_keys_in_memory(password)

    except Exception as e:
        print(f"Ошибка при загрузке ключей: {e}")


def encrypt_api_keys_in_memory(password):
    """Зашифровывает API ключи в памяти после их использования."""
    if PARAMS_API["api_key"] and PARAMS_API["api_secret"]:
        # Генерируем случайную соль для шифрования в памяти
        salt = secrets.token_bytes(SALT_SIZE)
        key = derive_key(password, salt)

        # Шифруем api_key и api_secret
        iv = secrets.token_bytes(16)  # Вектор инициализации
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(algorithms.AES.block_size).padder()

        encrypted_api_key = encrypt_data(PARAMS_API["api_key"].encode('utf-8'), encryptor, padder)
        encrypted_api_secret = encrypt_data(PARAMS_API["api_secret"].encode('utf-8'), encryptor, padder)

        # Сохраняем зашифрованные ключи и очищаем оригинальные
        PARAMS_API["encrypted_api_key"] = encrypted_api_key
        PARAMS_API["encrypted_api_secret"] = encrypted_api_secret
        clear_keys(PARAMS_API["api_key"], PARAMS_API["api_secret"])

        # Устанавливаем флаги для восстановления ключей при необходимости
        PARAMS_API["api_key"] = None
        PARAMS_API["api_secret"] = None


def decrypt_api_keys_in_memory(password):
    """Расшифровывает API ключи из памяти перед использованием."""
    if PARAMS_API["encrypted_api_key"] and PARAMS_API["encrypted_api_secret"]:
        # Извлекаем соль и генерируем ключ
        salt = secrets.token_bytes(SALT_SIZE)
        key = derive_key(password, salt)

        # Расшифровываем api_key и api_secret
        iv = secrets.token_bytes(16)  # Вектор инициализации
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        decrypted_api_key = decrypt_data(PARAMS_API["encrypted_api_key"], decryptor, unpadder).decode('utf-8')
        decrypted_api_secret = decrypt_data(PARAMS_API["encrypted_api_secret"], decryptor, unpadder).decode('utf-8')

        # Восстанавливаем оригинальные ключи
        PARAMS_API["api_key"] = decrypted_api_key
        PARAMS_API["api_secret"] = decrypted_api_secret


def encrypt_data(data, encryptor, padder):
    """Шифрует данные с использованием AES."""
    padded_data = padder.update(data) + padder.finalize()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return encrypted_data


def decrypt_data(data, decryptor, unpadder):
    """Расшифровывает данные с использованием AES."""
    padded_data = decryptor.update(data) + decryptor.finalize()
    decrypted_data = unpadder.update(padded_data) + unpadder.finalize()
    return decrypted_data


def check_usb_drive():
    """Проверяет наличие флешки с заданной меткой тома."""
    for partition in psutil.disk_partitions():
        if "removable" in partition.opts:  # Проверяем, является ли устройство съёмным
            try:
                volume_label = get_volume_label(partition.mountpoint)
                if volume_label == USB_DRIVE_LABEL:
                    print(f"Флешка найдена: {partition.mountpoint}")
                    return partition.mountpoint
            except Exception as e:
                print(f"Ошибка чтения метки тома: {e}")
    return None


def get_volume_label(drive):
    """Получает метку тома для указанного диска."""
    if sys.platform == "win32":
        import ctypes
        GetVolumeInformation = ctypes.windll.kernel32.GetVolumeInformationW
        label = ctypes.create_unicode_buffer(256)
        GetVolumeInformation(ctypes.c_wchar_p(drive), label, ctypes.sizeof(label), None, None, None, None, 0)
        return label.value
    else:
        raise NotImplementedError("Поддержка только Windows.")


def request_password():
    """Запрашивает пароль у пользователя."""
    password = input("Введите пароль для расшифровки секретного ключа: ")
    return password.strip() if password else None


def decrypt_secret_key(file_path, password):
    """Расшифровывает секретный ключ из файла."""
    try:
        with open(file_path, "rb") as f:
            encrypted_data = f.read()

        # Извлекаем соль, вектор инициализации и расшифровываем данные
        salt = encrypted_data[:SALT_SIZE]
        iv = encrypted_data[SALT_SIZE:SALT_SIZE + 16]
        cipher_text = encrypted_data[SALT_SIZE + 16:]

        key = derive_key(password, salt)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(cipher_text) + decryptor.finalize()

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(padded_data) + unpadder.finalize()

        return decrypted_data.decode('utf-8')

    except Exception as e:
        print(f"Ошибка расшифровки: {e}")
        return None


def derive_key(password, salt):
    """Генерирует ключ шифрования с использованием PBKDF2HMAC."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Размер ключа: 32 байта (256 бит)
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))


def parse_decrypted_key(decrypted_data):
    """Извлекает api_key и api_secret из расшифрованных данных."""
    try:
        lines = decrypted_data.splitlines()
        api_key = lines[0].split("=", 1)[1].strip()  # Формат: api_key=your_api_key
        api_secret = lines[1].split("=", 1)[1].strip()  # Формат: api_secret=your_api_secret
        return api_key, api_secret
    except Exception as e:
        print(f"Ошибка анализа ключей: {e}")
        return None, None


def clear_keys(*keys):
    """Очищает ключи из памяти."""
    for key in keys:
        if key:
            if isinstance(key, str):
                key = ''.join(['0' for _ in key])
            elif isinstance(key, bytes):
                key = b''.join([b'\x00' for _ in key])


if __name__ == "__main__":
    # Первое обращение к функции
    connection = get_connection_binance()
    if connection:
        print("Соединение успешно установлено.")
    else:
        print("Не удалось установить соединение.")

# from binance.error import ClientError
# from binance.spot import Spot
#
# PARAMS_API = {
#     "api_key": None,
#     "api_secret": None
# }
#
#
# def get_connection_binance():
#     try:
#         connection = Spot(PARAMS_API["api_key"], PARAMS_API["api_secret"])
#     except ClientError as error:
#         connection = False
#
#     return connection
