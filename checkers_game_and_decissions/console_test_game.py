from pvp_controller import PVPController
from report_item import ReportItem
from checkers_game import Color, Status

import cv2 as cv
import numpy as np


def present_game_state(game_report):

    game_state = game_report[ReportItem.GAME_STATE]

    img = np.zeros((500,500,3), np.uint8) #create black empty plane
    img[:,:] = (240,240,240) #setting background

    is_dark = False
    for x in range(0,8,1):  # drawing fields
        for y in range(0,8,1):

            if is_dark:
                cv.rectangle(img, (x*50+50,y*50+50),(x*50+100,y*50+100),(0,25,80),-1)
            else:
                cv.rectangle(img, (x*50+50,y*50+50),(x*50+100,y*50+100),(180,225,255),-1)
            
            is_dark = not is_dark
        is_dark = not is_dark
    
    for i in range(0,9,1):
        cv.line(img, [50 + i*50, 50], [50 + i*50, 450], (0,0,0), 3) #drawing vertical lines
        cv.line(img, [50, 50 + i*50], [450, 50 + i*50], (0,0,0), 3) #drawing horizontal lines

    for x,_ in enumerate(game_state): #drawing checkers
        for y,_ in enumerate(game_state[x]):
            if game_state[x][y] == 1:
                cv.circle(img, [x*50+75,y*50+75],20,(0,0,255),-1)
            if game_state[x][y] == 2:
                cv.circle(img, [x*50+75,y*50+75],20,(0,0,255),-1)
                cv.circle(img, [x*50+75,y*50+75],5,(255,255,255),-1)
            if game_state[x][y] == -1:
                cv.circle(img, [x*50+75,y*50+75],20,(0,255,0),-1)
            if game_state[x][y] == -2:
                cv.circle(img, [x*50+75,y*50+75],20,(0,255,0),-1)
                cv.circle(img, [x*50+75,y*50+75],5,(255,255,255),-1)


    cv.imshow("CHECKERS PVP - CONSOLE", img)

def print_state_report(report):
    print(f'''
=================================================
Turn of:    {report[ReportItem.TURN_OF].name if report[ReportItem.TURN_OF] is not None else ''}
Points:
    RED:    {report[ReportItem.POINTS][Color.RED]}
    GREEN:  {report[ReportItem.POINTS][Color.GREEN]}
Status:     {report[ReportItem.STATUS].name}
{'WINNER is '+ report[ReportItem.WINNER].name if report[ReportItem.STATUS]==Status.WON else ''}
=================================================
    ''')


def play_game(game_controller):

    while True:
        report = game_controller.report_state()

        print_state_report(report)

        present_game_state(report)
        if cv.waitKey(100) == ord('q'): #& 0xFF == ord('q'):
            break

        if report[ReportItem.STATUS] != Status.IN_PROGRESS:
            log = game_controller.get_log()
            print(f'\nLog of movements:\n{log}\n')
            print('Input anything to continue')
            input()
            break

        move = None
        while True:
            print ("Input your move: id_start id_finish (type 'h' to see possible moves, 'q' to end game)")

            player_input = input()

            if player_input == 'q':
                break
            if player_input == 'h':
                print('\nYour options are:')
                opts = report[ReportItem.OPTIONS]
                for o in opts:
                    print (o)
                print('\n')
                continue
            try:
                id_start = int(player_input.split(' ')[0])
                id_finish = int(player_input.split(' ')[1])
            except:
                continue

            moves_poss = report[ReportItem.OPTIONS]
            moves_chosen = []

            for m in moves_poss:
                if m[0] == id_start and m[len(m)-1] == id_finish:
                    moves_chosen.append(m)

            if len(moves_chosen) == 0:
                print('Wrong :( Try again')
            elif len(moves_chosen) == 1:
                move = moves_chosen[0]
                break
            else:
                print('\nSimilar moves - choose by index')
                for i, m in enumerate(moves_chosen):
                    print (f'{i} -> {m}')
                while True:
                    index = int(input())
                    if index >= 0 and index < len(moves_chosen):
                        move = moves_chosen[index]
                        break
                    else:
                        print('Wrong index')
                break

        if move is None:
            break

        game_controller.perform_move(move)


    cv.destroyAllWindows()

def main():
    game_controller = PVPController()

    while True:
        print('\nNEW GAME STARTED\n')

        play_game(game_controller)

        print ('\nDo you wish to replay? [y/n]')
        decission = input()
        if decission == 'y':
            game_controller.restart()
        else:
            break


if __name__ == "__main__":
    main()

    print('\nTHANKS FOR PLAYING! :D\n')