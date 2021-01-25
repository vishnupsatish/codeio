from flask import Markup

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from application.models.general import User


class InlineButtonWidget(object):
    html = """
    <button %s type="submit">%s</button>
    """

    def __init__(self, label, input_type='submit'):
        self.input_type = input_type
        self.label = label

    def __call__(self, **kwargs):
        param = []
        for key in kwargs:
            param.append(key + "=\"" + kwargs[key] + "\"")
        return Markup(self.html % (" ".join(param), self.label))


class StudentLoginForm(FlaskForm):
    code = StringField('Student Code', render_kw={'placeholder': 'Enter your student code'})
    submit = InlineButtonWidget('Login')


class SubmitSolutionForm(FlaskForm):
    language = SelectField('Language', validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    submit = InlineButtonWidget('Submit')
