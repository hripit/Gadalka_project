from binance.spot import Spot
from binance.error import ClientError
from parameters import PARAMS_BI


def get_connection_binance():
    try:
        connection = Spot(PARAMS_BI["api_key"], PARAMS_BI["api_secret"])
    except ClientError as error:
        connection = False

    return connection
