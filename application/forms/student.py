from flask import Markup, flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from application.models.general import User, Language


# class InlineButtonWidget:
#     html = """
#     <button %s type="submit">%s</button>
#     """
#
#     def __init__(self, label, input_type='submit'):
#         self.input_type = input_type
#         self.label = label
#
#     def __call__(self, **kwargs):
#         param = []
#         for key in kwargs:
#             param.append(key + "=\"" + kwargs[key] + "\"")
#         return Markup(self.html % (" ".join(param), self.label))


# The student login form
class StudentLoginForm(FlaskForm):
    # A string field to allow the student to enter their student code, along with a placeholder
    code = StringField('Student Code', render_kw={'placeholder': 'Enter your student code'})
    submit = SubmitField('Login')


# The form to allow students to submit
class SubmitSolutionForm(FlaskForm):
    language = SelectField('Language', validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Submit')

    # Ensure that the file extension matches the language's file extension
    def validate_file(self, file):
        lang = Language.query.filter_by(number=self.language.data).first()
        if lang.file_extension != file.data.filename.split('.')[-1]:
            flash('There were some errors uploading your file. Scroll down to view the error(s).', 'danger')
            raise ValidationError(f'Please upload a .{lang.file_extension} file.')
