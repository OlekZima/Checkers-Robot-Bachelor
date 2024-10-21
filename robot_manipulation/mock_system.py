from robot_manipulation.dobot_controller import DobotController as RealDobotController
#from mock_dobot_controller import DobotController as MockDobotController

def mock_system():
    dobot = RealDobotController(None)

    print('''
Welcome to movement tester for Dobot :)

To use it input movement in field ID notation, eg. 1 -6 10 -14 17
    ''')

    while True:
        print('\n\tInput your move, q to quit:')
        move_input = input()
        if move_input == 'q':
            break
        move = move_input.split(' ')
        for i,m in enumerate(move):
            move[i] = int(m)
        try:
            if move[len(move)-1] in [1,2,3,4]:
                dobot.perform_move(move, is_crown=True)
            else:
                dobot.perform_move(move, is_crown=False)
        except Exception as e:
            print(e)

    print('''
Thanks for using me to move DOBOT :)
    ''')

if __name__ == '__main__':
    mock_system()