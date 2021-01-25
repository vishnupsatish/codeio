import os
import secrets
from flask import render_template, url_for, flash, redirect, request, abort, session
from application import app, db, bcrypt
from application.forms.student import *
from application.models.general import *
from flask_login import login_user, current_user, logout_user, login_required


@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    form = StudentLoginForm()
    if form.validate_on_submit():
        student_identifier = form.code.data
        student = Student.query.filter_by(identifier=student_identifier).first()
        if student:
            session['student_id'] = form.code.data
            return redirect(url_for('student_submit_problem', class_identifier=request.args.get('class_identifier'),
                                    problem_identifier=request.args.get('problem_identifier')))
        print('lul')
    return render_template('student/general/login.html', form=form)


@app.route('/class/<string:class_identifier>/problem/<string:problem_identifier>/submit')
def student_submit_problem(class_identifier, problem_identifier):
    if 'student_id' not in session:
        return redirect(
            url_for('student_login', class_identifier=class_identifier, problem_identifier=problem_identifier))

    class_ = Class_.query.filter_by(identifier=class_identifier).first_or_404()
    problem = Problem.query.filter_by(identifier=problem_identifier, class_=class_).first_or_404()
    form = SubmitSolutionForm()
    form.language.choices = [(p.id, p.name) for p in problem.languages]
    # if form.validate_on_submit():
    #
    return render_template('student/general/submit.html', problem=problem, class_=class_, form=form)
