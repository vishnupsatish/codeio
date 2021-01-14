from flask import render_template, url_for, flash, redirect, request, abort
from application import app, db, bcrypt
from flask_login import login_user, current_user, logout_user, login_required
from flask_admin.contrib.sqla import ModelView
from application.forms.teacher import *
from application.settingssecrets import *


@app.route('/login')
def teacher_login():
    form = LoginForm()
    return render_template('teacher/general/login.html', form=form)


@app.route('/dashboard')
def teacher_dashboard():
    return render_template('teacher/general/dashboard.html')


@app.route('/class/1/home')
def teacher_class_home():
    return render_template('teacher/classes/home.html')


@app.route('/class/1/students')
def teacher_class_students():
    return render_template('teacher/classes/students.html')


@app.route('/class/1/new-problem')
def teacher_class_new_problem():
    return render_template('teacher/classes/new-problem.html')

