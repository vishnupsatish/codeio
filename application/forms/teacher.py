from flask import Flask, render_template, Markup
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectMultipleField, \
    SelectField, MultipleFileField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from wtforms.fields.html5 import DateField, URLField, TimeField
import time
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


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={'placeholder': 'Email'})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    remember = BooleanField('Remember Me')
    submit = InlineButtonWidget('Login')


class NewProblemForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description - Supports Markdown formatting', validators=[DataRequired(), Length(min=2, max=400)])
    time_limit = DecimalField('Time Limit', render_kw={'placeholder': 'Default: 5 sec'}, validators=[Optional()])
    memory_limit = IntegerField('Memory Limit', render_kw={'placeholder': 'Default: 512 MB'}, validators=[Optional()])
    allow_multiple_submissions = BooleanField('Allow multiple submissions')
    auto_grade = BooleanField('Auto Grade')
    total_marks = IntegerField('Marks out of:', validators=[DataRequired()])
    languages = SelectMultipleField('Languages', coerce=int, validators=[DataRequired()])

    input1file = FileField('Input File 1', validators=[FileAllowed(['txt'])])
    input2file = FileField('Input File 2', validators=[FileAllowed(['txt'])])
    input3file = FileField('Input File 3', validators=[FileAllowed(['txt'])])
    input4file = FileField('Input File 4', validators=[FileAllowed(['txt'])])
    input5file = FileField('Input File 5', validators=[FileAllowed(['txt'])])

    output1file = FileField('Output File 1', validators=[FileAllowed(['txt'])])
    output2file = FileField('Output File 2', validators=[FileAllowed(['txt'])])
    output3file = FileField('Output File 3', validators=[FileAllowed(['txt'])])
    output4file = FileField('Output File 4', validators=[FileAllowed(['txt'])])
    output5file = FileField('Output File 5', validators=[FileAllowed(['txt'])])

    submit = InlineButtonWidget('Create Problem')

    def validate_auto_grade(self, auto_grade):
        if self.input1file.data is None and auto_grade.data is True:
            raise ValidationError('Please enter at least one input file')

    def validate_output1file(self, output1file):
        if output1file.data is None and self.input1file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an output file')

    def validate_output2file(self, output2file):
        if output2file.data is None and self.input2file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an output file')

    def validate_output3file(self, output3file):
        if output3file.data is None and self.input3file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an output file')

    def validate_output4file(self, output4file):
        if output4file.data is None and self.input4file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an output file')

    def validate_output5file(self, output5file):
        if output5file.data is None and self.input5file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an output file')

    def validate_input1file(self, input1file):
        if input1file.data is None and self.output1file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an input file')

    def validate_input2file(self, input2file):
        if input2file.data is None and self.output2file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an input file')

    def validate_input3file(self, input3file):
        if input3file.data is None and self.output3file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an input file')

    def validate_input4file(self, input4file):
        if input4file.data is None and self.output4file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an input file')

    def validate_input5file(self, input5file):
        if input5file.data is None and self.output5file.data is not None and self.auto_grade.data is True:
            raise ValidationError('Please enter an input file')

    def validate_memory_limit(self, memory_limit):
        if memory_limit.data:
            if memory_limit.data < 3 or memory_limi.data > 512:
                raise ValidationError('The memory limit must be greater than 3 MB and no greater than 512 MB')

    def validate_time_limit(self, time_limit):
        if time_limit.data:
            if time_limit.data < 1 or time_limit.data > 5:
                raise ValidationError('The time limit must be greater than 1 second and no greater than 5 seconds', 'danger')


class NewClassForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description', validators=[Length(max=100)])
    submit = InlineButtonWidget('Create Class')


class NewStudentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    submit = InlineButtonWidget('Create Student')


class UpdateMarkForm(FlaskForm):
    mark = DecimalField('Mark', validators=[DataRequired()])
    submit = InlineButtonWidget('Update Mark')

    def __init__(self, problem_marks):
        self.problem_marks = problem_marks
        super(UpdateMarkForm, self).__init__()

    def validate_mark(self, mark):
        if mark.data > self.problem_marks:
            raise ValidationError(f'Must be less than or equal to {self.problem_marks}')