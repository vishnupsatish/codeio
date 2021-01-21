import boto3
import datetime as dt
from secrets import token_urlsafe
from werkzeug.utils import secure_filename
from flask import render_template, url_for, flash, redirect, request, abort
from application import app, db, bcrypt, admin
from flask_login import login_user, current_user, logout_user, login_required
from flask_admin.contrib.sqla import ModelView
from application.forms.teacher import *
from application.settingssecrets import *
from application.models.general import *
from application.utils import *

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Student, db.session))
admin.add_view(ModelView(Class_, db.session))
admin.add_view(ModelView(Problem, db.session))
admin.add_view(ModelView(Language, db.session))
admin.add_view(ModelView(InputFile, db.session))
admin.add_view(ModelView(OutputFile, db.session))
admin.add_view(ModelView(Submission, db.session))
admin.add_view(ModelView(Result, db.session))

s3 = boto3.resource('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name='ca-central-1')

UNSUCCESSFUL_LOGIN_MESSAGE = 'Login Unsuccessful. Please check email and password'
NOT_LOGGED_IN_MESSAGE = 'You must be logged in to view that page.'
CLASS_CREATED_MESSAGE = 'The class has been created successfully.'

bucket_name = 'code-execution-grade-10'


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('teacher_login'))


@app.route('/login', methods=['GET', 'POST'])
def teacher_login():
    if current_user.is_authenticated:
        return redirect(url_for('teacher_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('teacher_dashboard')) if not request.args.get('next') else redirect(
                url_for(request.args.get('next')))
        else:
            flash(UNSUCCESSFUL_LOGIN_MESSAGE, 'danger')
    return render_template('teacher/general/login.html', form=form)


@app.route('/dashboard')
def teacher_dashboard():
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login', next='teacher_dashboard'))
    classes_ = Class_.query.filter_by(user=current_user).all()
    return render_template('teacher/general/dashboard.html', classes_=classes_)


@app.route('/new-class', methods=['GET', 'POST'])
def new_class():
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login', next='new_class'))
    form = NewClassForm()
    if form.validate_on_submit():
        class_ = Class_(name=form.name.data, description=form.description.data, user=current_user,
                        identifier=token_urlsafe(16))
        db.session.add(class_)
        db.session.commit()
        flash(CLASS_CREATED_MESSAGE, 'success')
        return redirect(url_for('teacher_dashboard'))
    return render_template('teacher/general/new-class.html', form=form)


@app.route('/class/<string:identifier>/home')
def teacher_class_home(identifier):
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login'))
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()
    problems = Problem.query.filter_by(class_=class_).all()
    u = get_unique_students_problem(problems)
    return render_template('teacher/classes/home.html', problems=problems, class_=class_, identifier=identifier, u=u)


@app.route('/class/<string:identifier>/students')
def teacher_class_students(identifier):
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login'))
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()
    return render_template('teacher/classes/students.html', identifier=identifier)


@app.route('/class/<string:identifier>/new-problem', methods=['GET', 'POST'])
def teacher_class_new_problem(identifier):
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login'))
    class_ = Class_.query.filter_by(identifier=identifier, user=current_user).first_or_404()
    form = NewProblemForm()
    form.languages.choices = get_languages_form()
    if form.validate_on_submit():
        title = form.title.data

        description = form.description.data

        time_limit = form.time_limit.data
        memory_limit = form.memory_limit.data
        marks_out_of = form.total_marks.data

        languages = form.languages.data

        allow_multiple_submissions = form.allow_multiple_submissions.data
        auto_grade = form.auto_grade.data

        input1file = form.input1file.data
        input2file = form.input2file.data
        input3file = form.input3file.data
        input4file = form.input4file.data
        input5file = form.input5file.data

        output1file = form.output1file.data
        output2file = form.output2file.data
        output3file = form.output3file.data
        output4file = form.output4file.data
        output5file = form.output5file.data

        problem = Problem(user=current_user, title=title, description=description, total_marks=marks_out_of,
                          allow_multiple_submissions=allow_multiple_submissions, auto_grade=auto_grade,
                          identifier=token_urlsafe(8), class_=class_)
        if time_limit:
            problem.time_limit = time
        if memory_limit:
            problem.memory_limit = memory_limit

        for lang in languages:
            lang_object = Language.query.filter_by(number=int(lang)).first()
            problem.languages.append(lang_object)

        if auto_grade:
            inout1 = upload_input_output_file(1, input1file, output1file, class_, problem, s3, bucket_name)
            if inout1 is not None:
                flash(inout1, 'danger')
            inout2 = upload_input_output_file(1, input2file, output2file, class_, problem, s3, bucket_name)
            if inout2 is not None:
                flash(inout2, 'danger')
            inout3 = upload_input_output_file(1, input3file, output3file, class_, problem, s3, bucket_name)
            if inout3 is not None:
                flash(inout3, 'danger')
            inout4 = upload_input_output_file(1, input4file, output4file, class_, problem, s3, bucket_name)
            if inout4 is not None:
                flash(inout4, 'danger')
            inout5 = upload_input_output_file(1, input5file, output5file, class_, problem, s3, bucket_name)
            if inout5 is not None:
                flash(inout5, 'danger')

        db.session.commit()
        flash('The problem has been created successfully.', 'success')
        return redirect(url_for('teacher_class_home', identifier=identifier))

    return render_template('teacher/classes/new-problem.html', form=form, identifier=identifier)
