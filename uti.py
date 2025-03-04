from datetime import datetime, UTC, timedelta
from pandas import period_range
from dateutil.relativedelta import relativedelta


def repack_list(array: list):

    lst = [x for y in array for x in y]

    return lst


def dtime_range():
    """
    Для создания периода: в UTC, по умолчанию 1 год от начала текущего дня до текущего времени.
    :return: [start_dtime, end_dtime]
    """
    end_dtime = datetime.now(UTC)
    end_dtime = end_dtime.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    start_dtime = end_dtime - relativedelta(years=1)
    # start_dtime = start_dtime + timedelta(minutes=1)

    end_dtime = datetime.now(UTC)
    end_dtime = end_dtime.replace(second=0, microsecond=0, tzinfo=None)

    return [start_dtime, end_dtime]


def convert_to_timestamp(date_time: datetime):
    date_time = date_time.replace(tzinfo=UTC)
    return int(round(date_time.timestamp())) * 1000


def convert_from_timestamp(dtime) -> datetime:
    return datetime.fromtimestamp(int(dtime / 1000), UTC).replace(tzinfo=None)


def date_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
