from sys import exit

if __name__ == '__main__':

    choice = input('Get prices [0]. or Train model [1]. or Output result [2]: ')

    if choice == '0':
        print('Get prices [0]')
    elif choice == '1':
        print('Train model [1]')
    elif choice == '2':
        print('Output result [2]')
    else:
        exit()
