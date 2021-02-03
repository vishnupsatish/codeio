from flask import flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError
from application.models.general import Language


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
