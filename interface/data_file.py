from binance.error import ClientError
from binance.spot import Spot

1

def get_connection_binance():
    try:
        connection = Spot(PARAMS_API["api_key"], PARAMS_API["api_secret"])
    except ClientError as error:
        connection = False

    return connection
