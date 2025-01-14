from binance.spot import Spot
from binance.error import ClientError


def get_connection_binance():
    try:
        connection = Spot(PARAMS_API["api_key"], PARAMS_API["api_secret"])
    except ClientError as error:
        connection = False

    return connection