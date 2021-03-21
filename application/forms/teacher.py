from flask import flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectMultipleField, \
    IntegerField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, InputRequired
from application.models.general import User


# The registration form
class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()], render_kw={'placeholder': 'Name'})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={'placeholder': 'Email'})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')],
                                     render_kw={'placeholder': 'Confirm Password'})
    submit = SubmitField('Sign up')

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


# A form to update a teacher's account
class UpdateAccountForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    moss_code = StringField('MOSS Code')
    submit = SubmitField('Update account')


# A form to send a password reset email to the specified email address
class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send password reset email')


# A form to change the password of a user
class ChangePasswordForm(FlaskForm):
    password = PasswordField('New password', validators=[DataRequired()])
    submit = SubmitField('Change password')


# A form to send the confirmation email
class ConfirmAccountForm(FlaskForm):
    submit = SubmitField('Resend confirmation email')


# Confirmation to leaving a class
class LeaveClassForm(FlaskForm):
    submit = SubmitField('Leave class')


# Check for plagiarism form
class CheckPlagiarismForm(FlaskForm):
    submit = SubmitField('Check for plagiarism')


# The form to create a new class
class NewClassForm(FlaskForm):
    # The relevant fields as well as their validators
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description', validators=[Length(max=100)])
    submit = SubmitField('Create class')


# The form to create a new class
class UpdateClassForm(FlaskForm):
    # The relevant fields as well as their validators
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description', validators=[Length(max=100)])
    update = SubmitField('Update class')


# The form for a teacher to confirm their addition to a class
class ConfirmAdditionToClassForm(FlaskForm):
    submit = SubmitField('Join class as teacher')


# The form to create a new problem
class NewProblemForm(FlaskForm):
    # The relevant text, boolean, and select fields
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=45)])
    description = TextAreaField('Description - Supports Markdown formatting',
                                validators=[DataRequired(), Length(min=2, max=2500)])
    time_limit = DecimalField('Time Limit', render_kw={'placeholder': 'Default: 5 sec'}, validators=[Optional()])
    memory_limit = IntegerField('Memory Limit', render_kw={'placeholder': 'Default: 512 MB'}, validators=[Optional()])
    allow_multiple_submissions = BooleanField('Allow multiple submissions')
    visible = BooleanField('Visible to students')
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

    submit = SubmitField('Create problem')

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
        if output1file.data and len(output1file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if output1file.data:
            output1file.data.seek(0)

    def validate_output2file(self, output2file):
        if output2file.data is None and self.input2file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')
        if output2file.data and len(output2file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if output2file.data:
            output2file.data.seek(0)

    def validate_output3file(self, output3file):
        if output3file.data is None and self.input3file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')
        if output3file.data and len(output3file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if output3file.data:
            output3file.data.seek(0)

    def validate_output4file(self, output4file):
        if output4file.data is None and self.input4file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')
        if output4file.data and len(output4file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if output4file.data:
            output4file.data.seek(0)

    def validate_output5file(self, output5file):
        if output5file.data is None and self.input5file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an output file')
        if output5file.data and len(output5file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if output5file.data:
            output5file.data.seek(0)

    # For each input file, if there is a corresponding output file but no input file, throw an error
    def validate_input1file(self, input1file):
        if input1file.data is None and self.output1file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')
        if input1file.data and len(input1file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if input1file.data:
            input1file.data.seek(0)

    def validate_input2file(self, input2file):
        if input2file.data is None and self.output2file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')
        if input2file.data and len(input2file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if input2file.data:
            input2file.data.seek(0)

    def validate_input3file(self, input3file):
        if input3file.data is None and self.output3file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')
        if input3file.data and len(input3file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if input3file.data:
            input3file.data.seek(0)

    def validate_input4file(self, input4file):
        if input4file.data is None and self.output4file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')
        if input4file.data and len(input4file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if input4file.data:
            input4file.data.seek(0)

    def validate_input5file(self, input5file):
        if input5file.data is None and self.output5file.data is not None and self.auto_grade.data is True:
            flash('There were some errors creating the problem. Scroll down to see the error(s).', 'danger')
            raise ValidationError('Please enter an input file')
        if input5file.data and len(input5file.data.read()) / 8000000 > 1:
            return 'The maximum file size you can add is 8 megabytes.'
        if input5file.data:
            input5file.data.seek(0)

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


# The form to create a new student
class NewStudentForm(FlaskForm):
    # The student's name field, along with the DataRequired and Length validators and the submit button
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=45)])
    submit = SubmitField('Create student')


# The form to update the mark of a student
class UpdateMarkForm(FlaskForm):
    # The mark field, along with the InputRequired validator and the submit button
    # Note: the DataRequired validator is not used since it cannot accept
    # A value of 0, while the InputRequired validator can
    mark = DecimalField('Mark', validators=[InputRequired()])
    submit = SubmitField('Update mark')

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
    allow_more_submissions = BooleanField('Allow more submissions')
    visible = BooleanField('Visible to students')
    total_marks = IntegerField('Marks out of:', validators=[DataRequired()])
    languages = SelectMultipleField('Languages', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Update problem')

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
