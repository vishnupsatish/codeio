from flask import Flask, render_template, Markup, flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectMultipleField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, InputRequired
from application.models.general import User


# The registration form
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    # If a user already exists with that email, then throw an error
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


# The login form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={'placeholder': 'Email'})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


# The form to create a new problem
class NewProblemForm(FlaskForm):
    # The relevant text, boolean, and select fields
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description - Supports Markdown formatting',
                                validators=[DataRequired(), Length(min=2, max=2500)])
    time_limit = DecimalField('Time Limit', render_kw={'placeholder': 'Default: 5 sec'}, validators=[Optional()])
    memory_limit = IntegerField('Memory Limit', render_kw={'placeholder': 'Default: 512 MB'}, validators=[Optional()])
    allow_multiple_submissions = BooleanField('Allow multiple submissions')
    auto_grade = BooleanField('Auto Grade')
    total_marks = IntegerField('Marks out of:', validators=[DataRequired()])
    languages = SelectMultipleField('Languages', coerce=int, validators=[DataRequired()])

    # The input and output fields
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

    submit = SubmitField('Create Problem')

    # If auto grade was selected and the first input file was not selected, throw an error
    def validate_auto_grade(self, auto_grade):
        if self.input1file.data is None and auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter at least one input file')

    # For each output file, if there is a corresponding input file but no output file, throw an error
    def validate_output1file(self, output1file):
        if output1file.data is None and self.input1file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')

    def validate_output2file(self, output2file):
        if output2file.data is None and self.input2file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')

    def validate_output3file(self, output3file):
        if output3file.data is None and self.input3file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')

    def validate_output4file(self, output4file):
        if output4file.data is None and self.input4file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')

    def validate_output5file(self, output5file):
        if output5file.data is None and self.input5file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')

    # For each input file, if there is a corresponding output file but no input file, throw an error
    def validate_input1file(self, input1file):
        if input1file.data is None and self.output1file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')

    def validate_input2file(self, input2file):
        if input2file.data is None and self.output2file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')

    def validate_input3file(self, input3file):
        if input3file.data is None and self.output3file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')

    def validate_input4file(self, input4file):
        if input4file.data is None and self.output4file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')

    def validate_input5file(self, input5file):
        if input5file.data is None and self.output5file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')

    # Custom validators to make sure the memory limit and time limit aren't too high or too low
    def validate_memory_limit(self, memory_limit):
        if memory_limit.data:
            if memory_limit.data < 3 or memory_limit.data > 512:
                flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
                raise ValidationError('The memory limit must be greater than 3 MB and no greater than 512 MB')

    def validate_time_limit(self, time_limit):
        if time_limit.data:
            if time_limit.data < 1 or time_limit.data > 5:
                flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
                raise ValidationError('The time limit must be greater than 1 second and no greater than 5 seconds',
                                      'danger')


# The form to create a new class
class NewClassForm(FlaskForm):
    # The relevant fields as well as their validators
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description', validators=[Length(max=100)])
    submit = SubmitField('Create Class')


# The form to create a new student
class NewStudentForm(FlaskForm):
    # The student's name field, along with the DataRequired and Length validators and the submit button
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    submit = SubmitField('Create Student')


# The form to update the mark of a student
class UpdateMarkForm(FlaskForm):
    # The mark field, along with the InputRequired validator and the submit button
    # Note: the DataRequired validator is not used since it cannot accept
    # A value of 0, while the InputRequired validator can
    mark = DecimalField('Mark', validators=[InputRequired()])
    submit = SubmitField('Update Mark')

    # This is a super constructor for the class that
    # allows the problem's total marks to be passed in
    def __init__(self, problem_marks):
        # Set the attribute problem_marks to the inputted problem's marks
        self.problem_marks = problem_marks

        # Call the FlaskForm's constructor
        super(UpdateMarkForm, self).__init__()

    # Ensure that the mark is not negative and is less than or equal to the problem's total marks
    def validate_mark(self, mark):
        if mark.data > self.problem_marks or mark.data < 0:
            raise ValidationError(f'Must be less than or equal to {self.problem_marks} and greater than 0')


# The form to edit a problem
class EditProblemForm(FlaskForm):
    # Fields, such as title, description, time limit, etc, along with their validators
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description - Supports Markdown formatting',
                                validators=[DataRequired(), Length(min=2, max=2500)])
    time_limit = DecimalField('Time Limit', render_kw={'placeholder': 'Default: 5 sec'}, validators=[Optional()])
    memory_limit = IntegerField('Memory Limit', render_kw={'placeholder': 'Default: 512 MB'}, validators=[Optional()])
    allow_multiple_submissions = BooleanField('Allow multiple submissions')
    total_marks = IntegerField('Marks out of:', validators=[DataRequired()])
    languages = SelectMultipleField('Languages', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Update Problem')

    # Custom validators to make sure the memory limit and time limit aren't too high or too low
    def validate_memory_limit(self, memory_limit):
        if memory_limit.data:
            if memory_limit.data < 3 or memory_limit.data > 512:
                flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
                raise ValidationError('The memory limit must be greater than 3 MB and no greater than 512 MB')

    def validate_time_limit(self, time_limit):
        if time_limit.data:
            if time_limit.data < 1 or time_limit.data > 5:
                flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
                raise ValidationError('The time limit must be greater than 1 second and no greater than 5 seconds',
                                      'danger')
