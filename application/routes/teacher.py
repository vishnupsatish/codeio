from secrets import token_hex
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

UNSUCCESSFUL_LOGIN_MESSAGE = 'Login Unsuccessful. Please check email and password'
NOT_LOGGED_IN_MESSAGE = 'You must be logged in to view that page.'
CLASS_CREATED_MESSAGE = 'The class has been created successfully.'


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('teacher_login'))


@app.route('/login', methods=['GET', 'POST'])
def teacher_login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
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
        class_ = Class_(name=form.name.data, description=form.description.data, user=current_user, identifier=token_hex(16))
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
    return render_template('teacher/classes/home.html')


@app.route('/class/<string:identifier>/students')
def teacher_class_students(identifier):
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login'))
    return render_template('teacher/classes/students.html')


@app.route('/class/<string:identifier>/new-problem')
def teacher_class_new_problem(identifier):
    if not current_user.is_authenticated:
        flash(NOT_LOGGED_IN_MESSAGE, 'danger')
        return redirect(url_for('teacher_login'))
    form = NewProblemForm()
    form.languages.choices = get_languages_form()
    return render_template('teacher/classes/new-problem.html', form=form)
