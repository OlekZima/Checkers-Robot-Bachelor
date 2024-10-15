import os
import random
import uuid
from enum import Enum

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_api import status

from checkers_game_and_decissions.pvp_controller import PVPController
from checkers_game_and_decissions.report_item import ReportItem
from checkers_game_and_decissions.pvc_webgame_controller import PVCController
from checkers_game_and_decissions.checkers_game import Color, Status
from checkers_game_and_decissions.web_game_rsc.flask_forms.forms import IndexForm_join_game_id


class GameType(Enum):
    PVP = 1
    PVC = 2


class Game:
    games =[]

    @classmethod
    def create_game(cls, type = GameType.PVP):
        game_id = 1
        if len(Game.games) > 0:
            id_min = Game.games[0].game_id
            id_max = Game.games[0].game_id
            for g in Game.games:
                if g.game_id < id_min:
                    id_min = g.game_id
                if g.game_id > id_max:
                    id_max = g.game_id

            if id_min == 1:
                game_id = id_max + 1

        game = Game(game_id, type)
        Game.games.append(game)

        return game_id


    @classmethod
    def list_games(cls):

        resp = {
            'games': []
        }

        for g in Game.games:
            resp['games'].append(
                {
                    'game_id': g.game_id,
                    'game_status': g.game_controller.report_state()[ReportItem.STATUS].name
                }
            )

        return resp


    @classmethod
    def kill_game(cls, game_id):

        game = None

        for g in Game.games:
            if g.game_id == game_id:
                game = g

        if game is None:
            return False
        else:
            Game.games.remove(game)
            return True


    def __init__(self, game_id, type = GameType.PVP):
        self.players = {
            Color.GREEN: None,
            Color.RED: None
        }
        self.game_id = game_id
        self.type = type
        if self.type == GameType.PVP:
            self.game_controller = PVPController()
        if self.type == GameType.PVC:
            player_color = Color.GREEN if random.randint(1,2) == 1 else Color.RED
            computer_color = Color.GREEN if player_color == Color.RED else Color.RED
            self.players[computer_color] ={
                        'id': '',
                        'name': 'Michal\'s algorithm',
                        'endgame_informed': True
                    }
            self.game_controller = PVCController(human_color=player_color)


    def request_register_player(self, player_uuid, name):
        if self.players[Color.GREEN] is not None and self.players[Color.GREEN]['id'] == player_uuid:
            return True
        elif self.players[Color.RED] is not None and self.players[Color.RED]['id'] == player_uuid:
            return True
        else:
            if self.players[Color.GREEN] is None:
                self.players[Color.GREEN] ={
                    'id': player_uuid,
                    'name': name,
                    'endgame_informed': False
                }
                return True
            elif self.players[Color.RED] is None:
                self.players[Color.RED] = {
                    'id': player_uuid,
                    'name': name,
                    'endgame_informed': False
                }
                return True
            else:
                return False

    
    def request_give_state(self, player_uuid):
        if self.players[Color.GREEN] is not None and self.players[Color.GREEN]['id'] == player_uuid:
            state = self.game_controller.report_state()
            resp = {
                'my_color': 'GREEN',
                'my_name': self.players[Color.GREEN]['name'] if self.players[Color.GREEN] is not None else '',
                'opponent_name': self.players[Color.RED]['name'] if self.players[Color.RED] is not None else '',
                'game_board': state[ReportItem.GAME_STATE],
                'points': {
                    'GREEN': state[ReportItem.POINTS][Color.GREEN],
                    'RED': state[ReportItem.POINTS][Color.RED]
                },
                'status': state[ReportItem.STATUS].name,
                'winner': state[ReportItem.WINNER].name if state[ReportItem.WINNER] is not None else '',
                'options': state[ReportItem.OPTIONS] if state[ReportItem.TURN_OF] == Color.GREEN else [],
                'turn_of': state[ReportItem.TURN_OF].name if state[ReportItem.TURN_OF] is not None else ''
            }

            # Endgame cleaning after both players notified
            if state[ReportItem.STATUS] != Status.IN_PROGRESS:
                self.players[Color.GREEN]['endgame_informed'] = True
                if self.players[Color.RED]['endgame_informed'] == True:
                    Game.kill_game(self.game_id)

            return resp
        elif self.players[Color.RED] is not None and self.players[Color.RED]['id'] == player_uuid:
            state = self.game_controller.report_state()
            resp = {
                'my_color': 'RED',
                'my_name': self.players[Color.RED]['name'] if self.players[Color.RED] is not None else '',
                'opponent_name': self.players[Color.GREEN]['name'] if self.players[Color.GREEN] is not None else '',
                'game_board': state[ReportItem.GAME_STATE],
                'points': {
                    'GREEN': state[ReportItem.POINTS][Color.GREEN],
                    'RED': state[ReportItem.POINTS][Color.RED]
                },
                'status': state[ReportItem.STATUS].name,
                'winner': state[ReportItem.WINNER].name if state[ReportItem.WINNER] is not None else '',
                'options': state[ReportItem.OPTIONS] if state[ReportItem.TURN_OF] == Color.RED else [],
                'turn_of': state[ReportItem.TURN_OF].name if state[ReportItem.TURN_OF] is not None else ''
            }

            # Endgame cleaning after both players notified
            if state[ReportItem.STATUS] != Status.IN_PROGRESS:
                self.players[Color.RED]['endgame_informed'] = True
                if self.players[Color.GREEN]['endgame_informed'] == True:
                    Game.kill_game(self.game_id)

            return resp
        else:
            return None


    def request_move(self, player_uuid, move):

        state = self.game_controller.report_state()

        if self.players[state[ReportItem.TURN_OF]]['id'] == player_uuid:
            
            try:
                self.game_controller.perform_move(move)
                return True
            except Exception as e:
                print(str(e))
                return False

        else:
            return False


template_dir = os.path.abspath('checkers_game_and_decissions/web_game_rsc/templates')
static_relative = 'web_game_rsc/static'
static_dir = os.path.abspath('checkers_game_and_decissions'+'/'+static_relative)

app = Flask(__name__, template_folder=template_dir, static_url_path = static_dir, static_folder = static_relative)
app.config['SECRET_KEY'] = 'ef6d2c8a-c3b2-42bb-bab7-4372e682a2c5'


# Endpoint for the welcome page -> from which you can choose to start or join game
@app.route('/', methods=['GET'])
def index():
    return render_template('welcome.html.j2', form_join_game=IndexForm_join_game_id())


# If called without query params -> create new game and redirect
# Id query param has game id -> ask to join it
@app.route('/game', methods=['GET'])
def get_game():
    
    game_id = request.args.get('game_id')
    name = request.args.get('name')
    user_uuid = request.args.get('user_uuid')
    game_type_arg = request.args.get('type')

    # for players with no uuid already - need to process them first, 
    # and then redirect again with uuid for them to not loose it
    if user_uuid is None or user_uuid == '':
        
        # must have been field being left empty
        if game_id == '':
            return 'Id of game is obligatory', status.HTTP_400_BAD_REQUEST
        
        #create name artificially if user forgot to
        if name is None or name == '': 
            name = 'Noname'+str(random.randint(111,999))

        # if no game specified - create one and redirect user to join it
        # additionally check for game type of request (PVP/PVC)
        if game_id is None:
            
            if game_type_arg is None or game_type_arg == '':
                return 'Must specify game type (Player vs Player or Player vs Computer)', status.HTTP_400_BAD_REQUEST
            
            if game_type_arg == 'PVP':
                game_type = GameType.PVP
            elif game_type_arg == 'PVC':
                game_type = GameType.PVC
            else:
                return 'Invalid game type, choose from [PVP, PVC] (Player vs Player or Player vs Computer)', status.HTTP_400_BAD_REQUEST
            
            # create game and receive its id
            game_id = Game.create_game(type = game_type)

            return redirect(url_for('get_game')+'?game_id='+str(game_id)+'&name='+str(name))

        # if user is ready - let him join game with created uuid
        if game_id is not None: 
            user_uuid = str(uuid.uuid4())
            return redirect(url_for('get_game')+'?game_id='+str(game_id)+'&name='+str(name)+'&user_uuid='+user_uuid)
    else:
        if name is None or name == '' or game_id is None:
            return 'Bad request', status.HTTP_400_BAD_REQUEST

        # check if game exist, if user is playing it or if there is free slot - if not return 404
        game = None
        for g in Game.games:
            if g.game_id == int(game_id):
                game = g
                break
        if game is None:
            return 'Game does not exist', 404

        if game.request_register_player(user_uuid, name):
            return render_template('pvp_game.html.j2', game_id = game_id, name=name, user_uuid=user_uuid)
        else:
            return 'Unauthorized', 401 


@app.route('/game_status', methods=['GET'])
def get_game_status():

    game_id = request.args.get('game_id')
    user_uuid = request.args.get('user_uuid')

    if game_id is None or game_id == '' or user_uuid is None or user_uuid == '':
        return 'Bad request', status.HTTP_400_BAD_REQUEST

    game = None
    for g in Game.games:
        if g.game_id == int(game_id):
            game = g
            break
    if game is None:
        return 'Game does not exist', 404
    
    if game.request_register_player(user_uuid, None):
        return jsonify(game.request_give_state(user_uuid))
    else:
        return 'Unauthorized', 401


@app.route('/move', methods=['POST'])
def perform_move():

    json = request.json

    user_uuid = json['user_uuid']
    game_id = json['game_id']
    move = json['move']

    if game_id is None or game_id == '' or user_uuid is None or user_uuid == '':
        return 'Bad request', status.HTTP_400_BAD_REQUEST

    game = None
    for g in Game.games:
        if g.game_id == int(game_id):
            game = g
            break
    if game is None:
        return 'Game does not exist', 404
    
    if game.request_register_player(user_uuid, None):
        
        move = [int(m) for m in move]

        if game.request_move(user_uuid, move):
            return "Move performed", status.HTTP_200_OK
        else:
            return "Invalid movement or not your turn", status.HTTP_400_BAD_REQUEST

    else:
        return 'Unauthorized', 401


@app.route('/kill', methods=['DELETE'])
def kill_game():

    game_id = request.args.get('game_id')
    
    if game_id == '' or game_id is None:
        return 'Bad request', status.HTTP_400_BAD_REQUEST

    game_id = int(game_id)

    if Game.kill_game(game_id):
        return "Game killed", 200
    else:
        return "Game not found", status.HTTP_404_NOT_FOUND


@app.route('/list', methods=['GET'])
def list_games():

    return jsonify(Game.list_games())



if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8098', debug=True)

def run_web_game():
    app.run(host='0.0.0.0', port='8098', debug=True)