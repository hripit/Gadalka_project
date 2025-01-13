from datetime import datetime


def convert_timestamp(dtime):
    return datetime.fromtimestamp(int(dtime / 1000))


def date_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")