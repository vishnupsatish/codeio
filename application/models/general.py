import datetime as dt
from application import db, login_manager, app
from flask_login import UserMixin


# IMPORTANT: ALL TIME ARE STORED IN EPOCH SECONDS, MUST CONVERT TO USER'S LOCAL TIME ZONE

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class_student_association_table = db.Table('class_student_association', db.Model.metadata,
                                           db.Column('class_id', db.Integer, db.ForeignKey('class_.id')),
                                           db.Column('student_id', db.Integer, db.ForeignKey('student.id'))
                                           )

problem_language_association_table = db.Table('problem_language_association', db.Model.metadata,
                                              db.Column('problem_id', db.Integer, db.ForeignKey('problem.id')),
                                              db.Column('language_id', db.Integer, db.ForeignKey('language.id'))
                                              )


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    classes_ = db.relationship('Class_', backref='user', lazy=True)
    problems = db.relationship('Problem', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    submissions = db.relationship('Submission', backref='student', lazy=True)


class Class_(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problems = db.relationship('Problem', backref='class_', lazy=True)
    students = db.relationship('Student', secondary=class_student_association_table, lazy=True,
                               backref='classes_')


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String, nullable=False)
    title = db.Column(db.String(45), nullable=False)
    description = db.Column(db.String, nullable=False)
    time_limit = db.Column(db.Float, nullable=False, default=5)
    memory_limit = db.Column(db.Integer, nullable=False, default=768)
    total_marks = db.Column(db.Integer, nullable=False)
    auto_grade = db.Column(db.Boolean, nullable=False, default=False)
    allow_multiple_submissions = db.Column(db.Boolean, nullable=False, default=False)
    create_date_time = db.Column(db.DateTime, nullable=False)
    input_files = db.relationship('InputFile', backref='problem', lazy=True)
    output_files = db.relationship('OutputFile', backref='problem', lazy=True)
    submissions = db.relationship('Submission', backref='problem', lazy=True)
    languages = db.relationship('Language', secondary=problem_language_association_table, lazy=True,
                                backref='problems')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class_.id'), nullable=False)


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    submissions = db.relationship('Submission', backref='language', lazy=True)


class InputFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    file_path = db.Column(db.String, nullable=False)
    file_name = db.Column(db.String, nullable=False)
    file_size = db.Column(db.String)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    output_file = db.relationship('OutputFile', backref='input_file', lazy=True, uselist=False)
    results = db.relationship('Result', backref='input_file', lazy=True)


class OutputFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    file_path = db.Column(db.String, nullable=False)
    file_name = db.Column(db.String, nullable=False)
    file_size = db.Column(db.String)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    input_id = db.Column(db.Integer, db.ForeignKey('input_file.id'), nullable=False)
    results = db.relationship('Result', backref='output_file', lazy=True)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String, nullable=False)
    file_name = db.Column(db.String, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    file_size = db.Column(db.String)
    marks = db.Column(db.Integer)
    results = db.relationship('Result', backref='submission', lazy=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'), nullable=False)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_id = db.Column(db.Integer, db.ForeignKey('input_file.id'), nullable=False)
    output_id = db.Column(db.Integer, db.ForeignKey('output_file.id'), nullable=False)

    token = db.Column(db.String, nullable=False)
    stderr = db.Column(db.String)
    stdout = db.Column(db.String)
    message = db.Column(db.String)
    time = db.Column(db.String)
    memory = db.Column(db.Integer)
    compile_output = db.Column(db.String)

    status_id = db.Column(db.Integer)
    status_description = db.Column(db.String)

    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), nullable=False)
