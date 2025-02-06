from sys import exit
from get_prices.get_trade_history import get_prices
from interface.trade_app import start_app


if __name__ == '__main__':
    # get_prices()
    # # start_app()

    choice = input('Get prices [0]. or Train model [1]. or Output result [2] or Start interface [5]: ')

    if choice == '0':
        get_prices()
    elif choice == '1':
        print('Train model [1]')
    elif choice == '2':
        print('Output result [2]')
    elif choice == '5':
        start_app()
    else:
        exit()
