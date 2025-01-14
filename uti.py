from datetime import datetime, UTC, timedelta
from pandas import period_range
from dateutil.relativedelta import relativedelta


def dtime_range():
    """
    Для создания периода по умолчанию.
    :return: [start_dtime, end_dtime]
    """
    end_dtime = datetime.now(UTC).replace(tzinfo=None)

    end_dtime = end_dtime.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)

    start_dtime = end_dtime - relativedelta(years=1)
    start_dtime = start_dtime + timedelta(seconds=1)

    return [start_dtime, end_dtime]


def convert_to_timestamp(date_time):
    return int(round(date_time.timestamp())) * 1000


def convert_timestamp(dtime):
    return datetime.fromtimestamp(int(dtime / 1000))


def date_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")