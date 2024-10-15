from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SelectField

class IndexForm_join_game_id(FlaskForm):
    game_id = IntegerField('Id of game')
    name = StringField('Your name')
    type = SelectField('Game Type',choices = [
        ('PVP', 'Player vs Player'),
        ('PVC', 'Player vs Computer')
    ])