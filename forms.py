from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, ValidationError, InputRequired
from models import User

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)],
                           render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Register')

    # noinspection PyMethodMayBeStatic
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)],
                           render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login')