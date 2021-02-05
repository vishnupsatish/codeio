from application import db, login_manager, app
from flask_login import UserMixin


# A requirement of flask-login, let it know how to handle login_user and logout_user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# A many-to-many relationship between problems and languages
problem_language_association_table = db.Table('problem_language_association', db.Model.metadata,
                                              db.Column('problem_id', db.Integer, db.ForeignKey('problem.id')),
                                              db.Column('language_id', db.Integer, db.ForeignKey('language.id'))
                                              )


# A user table
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    # Fields such as email, password, and name
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)

    # The classes and problems that the user has created
    classes_ = db.relationship('Class_', backref='user', lazy=True)
    problems = db.relationship('Problem', backref='user', lazy=True)


# A student table
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Name and student code (identifier)
    name = db.Column(db.String, nullable=False)
    identifier = db.Column(db.String, nullable=False)

    # The submissions the student has made
    submissions = db.relationship('Submission', backref='student', lazy=True, cascade="all, delete")

    # The class the student is associated to
    class_id = db.Column(db.Integer, db.ForeignKey('class_.id'), nullable=False)


# A class table
class Class_(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Identifier, name, and the description of the class
    identifier = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)

    # The user that created the class
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The problems associated to that class
    problems = db.relationship('Problem', backref='class_', lazy=True, cascade="all, delete")

    # The students in that class
    students = db.relationship('Student', backref='class_', lazy=True, cascade="all, delete")


# A problem table
class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The problem's identifier, title, description (in markdown
    # and html), time_limit, and other relevant fields
    identifier = db.Column(db.String, nullable=False)
    title = db.Column(db.String(45), nullable=False)
    description = db.Column(db.String, nullable=False)
    description_html = db.Column(db.String, nullable=False)
    time_limit = db.Column(db.Float, nullable=False, default=5.0)
    memory_limit = db.Column(db.Integer, nullable=False, default=512)
    total_marks = db.Column(db.Integer, nullable=False)
    auto_grade = db.Column(db.Boolean, nullable=False, default=False)
    allow_multiple_submissions = db.Column(db.Boolean, nullable=False, default=False)
    allow_more_submissions = db.Column(db.Boolean, nullable=False, default=True)
    create_date_time = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # The input and output files associated to that problem
    input_files = db.relationship('InputFile', backref='problem', lazy=True, cascade="all, delete")
    output_files = db.relationship('OutputFile', backref='problem', lazy=True, cascade="all, delete")

    # The submissions associated to that problem
    submissions = db.relationship('Submission', backref='problem', lazy=True, cascade="all, delete")

    # The languages associated to that problem (many-to-many using the association table)
    languages = db.relationship('Language', secondary=problem_language_association_table, lazy=True,
                                backref='problems')

    # The user who created the problem
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The class that the problem is in
    class_id = db.Column(db.Integer, db.ForeignKey('class_.id'), nullable=False)


# A language table
class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The number (Judge0 id), name, and file extension of the language's source file
    number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    file_extension = db.Column(db.String, nullable=False)

    # The submissions associated to that language
    submissions = db.relationship('Submission', backref='language', lazy=True)


# A table that contains every input file
class InputFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The number, file path, and file size of the input file
    number = db.Column(db.Integer)
    file_path = db.Column(db.String, nullable=False)
    file_size = db.Column(db.Integer)

    # The problem that the input file is a part of
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)

    # The output file that is associated to the input file
    output_file = db.relationship('OutputFile', backref='input_file', lazy=True, uselist=False, cascade="all, delete")

    # The results associated to the input file
    results = db.relationship('Result', backref='input_file', lazy=True, cascade="all, delete")


# A table that contains every output file
class OutputFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The number, file path, and file size of the input file
    number = db.Column(db.Integer)
    file_path = db.Column(db.String, nullable=False)
    file_size = db.Column(db.String)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)

    # The input file that is associated to the output file
    input_id = db.Column(db.Integer, db.ForeignKey('input_file.id'), nullable=False)

    # The results associated to the output file
    results = db.relationship('Result', backref='output_file', lazy=True, cascade="all, delete")


# A submission table
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The UUID (also the task id), file_path of the code, the date and time
    # in which it was submitted, the file_size, and the marks it earned
    uuid = db.Column(db.String, nullable=False)
    file_path = db.Column(db.String, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    file_size = db.Column(db.Integer)
    total_marks = db.Column(db.Integer)

    # Not used as of now... to be used to handle Internal Errors
    marks = db.Column(db.Integer)

    # Whether the submission has finished executing in Judge0 or not
    done = db.Column(db.Boolean, default=False)

    # The results associated to the submission
    results = db.relationship('Result', backref='submission', lazy=True, cascade="all, delete")

    # The problem, student, and language that is the submission is a part of
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'), nullable=False)


# A result table
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The input and output files associated to the result
    input_id = db.Column(db.Integer, db.ForeignKey('input_file.id'), nullable=False)
    output_id = db.Column(db.Integer, db.ForeignKey('output_file.id'), nullable=False)

    # The Judge0 token of the result
    token = db.Column(db.String, nullable=False)

    # The standard error, standard output, time and memory token, compile
    # output, expected output, and whether or not the result was correct
    stderr = db.Column(db.String)
    stdout = db.Column(db.String)
    time = db.Column(db.String)
    memory = db.Column(db.Integer)
    compile_output = db.Column(db.String)
    expected_output = db.Column(db.String)
    correct = db.Column(db.Boolean)

    # The marks that the result earned the the total marks of the submission
    marks = db.Column(db.Float)
    marks_out_of = db.Column(db.Float)

    # The submission that the result is associated with
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)

    # The status that the result is associated with
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=False)


# A table that contains every Judge0 status
class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # The Judge0 number and name of the status
    number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)

    # The results that the status is associated with
    results = db.relationship('Result', backref='status', lazy=True)
